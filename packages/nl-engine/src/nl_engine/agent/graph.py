"""LangGraph wiring for the conversational ReAct agent.

Builds a `StateGraph` with two nodes — the LLM-call node (`agent_step`)
and the tool-execution node (`tools`). Step accounting + the typed
`final_answer` terminal are layered on top of LangGraph's
`create_react_agent` semantics so we keep the prebuilt's loop while
enforcing our own invariants:

  * Hard cap of 10 LLM calls per turn (state.MAX_STEPS_PER_TURN).
  * Turn ends on a `final_answer` or `clarify` tool call, OR on cap.
  * The LangChain layer never escapes this module; persistence.py
    converts in/out at the edges.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from nl_engine.agent.state import MAX_STEPS_PER_TURN, AgentState
from nl_engine.agent.tools import ALL_TOOLS, serialize_tool_result

_TERMINAL_TOOLS = {"final_answer", "clarify"}

# OpenUI system prompt — committed artifact regenerated via
# `make openui-prompt`. ~20K chars; teaches the agent to emit
# valid OpenUI Lang DSL via `final_answer.openui_dsl` (HUG-178 Phase B).
#
# The committed artifact is written for free-text DSL emission ("Your
# ENTIRE response must be valid openui-lang code"), which is hostile to
# our tool-calling flow. We wrap it with a preamble that re-frames it
# as a reference grammar: tools come first, OpenUI DSL goes inside the
# `final_answer.openui_dsl` argument when a chart/widget is appropriate.
_OPENUI_REFERENCE = (Path(__file__).parent / "openui_prompt.txt").read_text(
    encoding="utf-8"
)
_OPENUI_SYSTEM_PROMPT = (
    "You are a lending-analytics agent for a credit union. Answer the "
    "user's question by calling the registered tools (list_metrics, "
    "lookup_metric_definition, mf_query) to gather data, then terminate "
    "the turn by calling the `final_answer` tool exactly once.\n\n"
    "The `final_answer.openui_dsl` argument accepts a valid OpenUI Lang "
    "DSL string — populate it whenever the answer benefits from a "
    "chart, table, KPI tile, or layout. Use only the components in the "
    "library below. Stay strictly within the openui-lang syntax rules. "
    "If the answer is purely textual, leave `openui_dsl` empty.\n\n"
    "The `summary` argument is shown in every case. `rows` and "
    "`mf_query` should be populated from the mf_query tool result when "
    "you used it.\n\n"
    "DO NOT respond with raw openui-lang text in the message body — "
    "that bypasses our tool-call protocol. The DSL belongs inside "
    "`final_answer.openui_dsl`, not in the assistant message content.\n\n"
    "=== OpenUI Lang reference (apply only to `openui_dsl` argument) ===\n\n"
) + _OPENUI_REFERENCE
_STEP_CAP_MESSAGE = (
    "I couldn't reach an answer within the {cap}-step limit for this turn. "
    "Try rephrasing or breaking the question into smaller parts."
)


def _last_ai_message(messages: list[BaseMessage]) -> AIMessage | None:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _route(state: AgentState) -> str:
    """Decide whether to dispatch tools, terminate, or continue looping."""
    if state.step_count >= MAX_STEPS_PER_TURN:
        return "step_cap"
    last_ai = _last_ai_message(state.messages)
    if last_ai is None or not last_ai.tool_calls:
        return END
    for call in last_ai.tool_calls:
        if call["name"] in _TERMINAL_TOOLS:
            return "tools_terminal"
    return "tools"


def _make_tools_node(tools: list[BaseTool]) -> Any:
    by_name = {t.name: t for t in tools}

    def run_tools(state: AgentState) -> dict[str, Any]:
        last_ai = _last_ai_message(state.messages)
        if last_ai is None or not last_ai.tool_calls:
            return {}
        new_messages: list[BaseMessage] = []
        for call in last_ai.tool_calls:
            tool = by_name.get(call["name"])
            if tool is None:
                result: Any = {"error": f"unknown tool: {call['name']}"}
            else:
                try:
                    result = tool.invoke(call.get("args", {}))
                except Exception as exc:  # noqa: BLE001 — surfaced to LLM
                    result = {"error": str(exc)}
            new_messages.append(
                ToolMessage(
                    content=serialize_tool_result(result),
                    tool_call_id=call.get("id", "unknown"),
                    name=call["name"],
                )
            )
        return {"messages": new_messages}

    return run_tools


def _ensure_system_prompt(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Return the message list with the OpenUI SystemMessage prepended.

    Attached transiently per-call and not written back into graph state,
    so checkpointed threads don't carry the ~20KB prompt on every row.
    The check on `messages[0]` is defensive — if a thread is ever loaded
    with a SystemMessage already at the head, it's left alone.
    """
    if messages and isinstance(messages[0], SystemMessage):
        return messages
    return [SystemMessage(content=_OPENUI_SYSTEM_PROMPT), *messages]


def _make_agent_step(llm: BaseChatModel, tools: list[BaseTool]) -> Any:
    bound = llm.bind_tools(tools)

    def agent_step(state: AgentState) -> dict[str, Any]:
        msgs = _ensure_system_prompt(state.messages)
        response = bound.invoke(msgs)
        return {"messages": [response], "step_count": state.step_count + 1}

    return agent_step


def _step_cap_node(state: AgentState) -> dict[str, Any]:
    return {
        "messages": [
            AIMessage(content=_STEP_CAP_MESSAGE.format(cap=MAX_STEPS_PER_TURN))
        ]
    }


def build_graph(
    llm: BaseChatModel,
    tools: list[BaseTool] | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Compile the StateGraph. Pass `checkpointer=PostgresSaver(...)` in
    production; tests use the default in-memory MemorySaver via None."""
    selected_tools = tools or list(ALL_TOOLS)
    graph = StateGraph(AgentState)
    graph.add_node("agent_step", _make_agent_step(llm, selected_tools))
    graph.add_node("tools", _make_tools_node(selected_tools))
    graph.add_node("tools_terminal", _make_tools_node(selected_tools))
    graph.add_node("step_cap", _step_cap_node)
    graph.add_edge(START, "agent_step")
    graph.add_conditional_edges(
        "agent_step",
        _route,
        {
            "tools": "tools",
            "tools_terminal": "tools_terminal",
            "step_cap": "step_cap",
            END: END,
        },
    )
    graph.add_edge("tools", "agent_step")
    graph.add_edge("tools_terminal", END)
    graph.add_edge("step_cap", END)
    return graph.compile(checkpointer=checkpointer)
