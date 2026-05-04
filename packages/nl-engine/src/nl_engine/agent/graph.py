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

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from nl_engine.agent.state import MAX_STEPS_PER_TURN, AgentState
from nl_engine.agent.tools import ALL_TOOLS, serialize_tool_result

_TERMINAL_TOOLS = {"final_answer", "clarify"}
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


def _make_agent_step(llm: BaseChatModel, tools: list[BaseTool]) -> Any:
    bound = llm.bind_tools(tools)

    def agent_step(state: AgentState) -> dict[str, Any]:
        response = bound.invoke(state.messages)
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
