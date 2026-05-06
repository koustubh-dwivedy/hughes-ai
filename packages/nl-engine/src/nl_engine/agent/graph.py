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

import logging
import os
import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from nl_engine.agent.llm_invoke import (
    AGENT_STEP_DEFAULT_TIMEOUT_S,
    invoke_with_wall_timeout,
    is_transient_llm_error,
)
from nl_engine.agent.state import MAX_STEPS_PER_TURN, AgentState
from nl_engine.agent.system_prompt import SYSTEM_PROMPT as _OPENUI_SYSTEM_PROMPT
from nl_engine.agent.tools import ALL_TOOLS, serialize_tool_result

log = logging.getLogger(__name__)

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


# Token-overflow guard threshold (HUG-190 Phase C). Both Qwen 3 32B and
# Gemma 4 31B have 128K-131K context windows; we trim long histories at
# 100K to leave headroom for the system prompt + tool descriptions +
# the LLM's own response. Heuristic estimate: ~4 chars per token.
_TOKEN_BUDGET = 100_000
_CHARS_PER_TOKEN_HEURISTIC = 4


def _estimate_tokens(messages: list[BaseMessage]) -> int:
    """Rough character-based token estimate. Fast (no tokenizer dep)
    and good enough to decide when to truncate. Real budget happens
    inside the LLM provider; this is just to avoid sending obviously-
    over-budget requests."""
    total_chars = 0
    for msg in messages:
        content = msg.content
        if isinstance(content, str):
            total_chars += len(content)
        else:
            # AIMessage with structured content (tool calls) — best-effort
            # serialization length.
            total_chars += len(str(content))
    return total_chars // _CHARS_PER_TOKEN_HEURISTIC


def _truncate_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """If the message list exceeds the token budget, drop the oldest
    non-system messages in pairs until it fits. Preserves the system
    prompt (always kept) and the tail of the conversation (the most
    recent context the LLM actually needs).

    HUG-190 Phase C: prevents context-overflow exceptions from crashing
    the agent on long threads.
    """
    if _estimate_tokens(messages) <= _TOKEN_BUDGET:
        return messages
    system: list[BaseMessage] = []
    rest: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            system.append(msg)
        else:
            rest.append(msg)
    dropped = 0
    while rest and _estimate_tokens(system + rest) > _TOKEN_BUDGET:
        # Drop the oldest non-system message.
        rest.pop(0)
        dropped += 1
    if dropped:
        log.warning(
            "agent history truncated: dropped %d oldest non-system messages "
            "to fit %d-token budget",
            dropped,
            _TOKEN_BUDGET,
        )
    return system + rest


_AGENT_ERROR_FALLBACK = (
    "I hit an error while thinking about that question. The system has "
    "logged the details. Please try rephrasing or breaking the question "
    "into smaller parts."
)

_LLM_MAX_RETRIES = 2  # 1 original + 2 retries = 3 total attempts
_LLM_RETRY_BACKOFF_BASE_S = 1.0  # exponential: 1s, 2s


def _make_agent_step(llm: BaseChatModel, tools: list[BaseTool]) -> Any:
    bound = llm.bind_tools(tools)
    wall_timeout = float(
        os.environ.get("AGENT_STEP_TIMEOUT_S", AGENT_STEP_DEFAULT_TIMEOUT_S)
    )

    def agent_step(state: AgentState) -> dict[str, Any]:
        msgs = _truncate_history(_ensure_system_prompt(state.messages))
        last_exc: Exception | None = None
        for attempt in range(_LLM_MAX_RETRIES + 1):
            try:
                response = invoke_with_wall_timeout(bound, msgs, wall_timeout)
                return {
                    "messages": [response],
                    "step_count": state.step_count + 1,
                }
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < _LLM_MAX_RETRIES and is_transient_llm_error(exc):
                    backoff = _LLM_RETRY_BACKOFF_BASE_S * (2**attempt)
                    log.warning(
                        "agent_step LLM transient error (attempt %d/%d, "
                        "retrying in %.1fs): %s",
                        attempt + 1,
                        _LLM_MAX_RETRIES + 1,
                        backoff,
                        str(exc)[:200],
                    )
                    time.sleep(backoff)
                    continue
                break
        # Fall-through: non-transient error OR retries exhausted.
        # Surface as graceful AIMessage so the SSE stream stays alive.
        log.warning(
            "agent_step LLM error after %d attempt(s) (%s): %s",
            (_LLM_MAX_RETRIES + 1)
            if last_exc and is_transient_llm_error(last_exc)
            else 1,
            type(last_exc).__name__ if last_exc else "Unknown",
            str(last_exc)[:300] if last_exc else "",
        )
        return {
            "messages": [AIMessage(content=_AGENT_ERROR_FALLBACK)],
            "step_count": state.step_count + 1,
        }

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
