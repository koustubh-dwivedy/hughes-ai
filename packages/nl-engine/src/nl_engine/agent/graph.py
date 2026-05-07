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

import structlog.contextvars
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from nl_engine.agent.history import ensure_system_prompt, truncate_history
from nl_engine.agent.llm_invoke import (
    AGENT_STEP_DEFAULT_TIMEOUT_S,
    is_transient_llm_error,
    stream_with_wall_timeout,
)
from nl_engine.agent.state import MAX_STEPS_PER_TURN, AgentState
from nl_engine.agent.streaming_summary import make_summary_streamer
from nl_engine.agent.tools import ALL_TOOLS, serialize_tool_result
from nl_engine.logging import bind_request_id, get_logger

log = logging.getLogger(__name__)
slog = get_logger().bind(component="agent.graph")

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
    from nl_engine.agent.metrics import (
        agent_tool_calls_total,
        agent_tool_duration_seconds,
    )

    by_name = {t.name: t for t in tools}

    def run_tools(state: AgentState) -> dict[str, Any]:
        if state.request_id:
            structlog.contextvars.bind_contextvars(request_id=state.request_id)
        last_ai = _last_ai_message(state.messages)
        if last_ai is None or not last_ai.tool_calls:
            return {}
        new_messages: list[BaseMessage] = []
        for call in last_ai.tool_calls:
            name = call["name"]
            agent_tool_calls_total.labels(tool=name).inc()
            tool = by_name.get(name)
            t0 = time.monotonic()
            if tool is None:
                result: Any = {"error": f"unknown tool: {name}"}
                slog.warning("agent.unknown_tool", tool=name)
            else:
                try:
                    result = tool.invoke(call.get("args", {}))
                except Exception as exc:  # noqa: BLE001 — surfaced to LLM
                    result = {"error": str(exc)}
                    slog.warning(
                        "agent.tool_exception",
                        tool=name,
                        error_type=type(exc).__name__,
                        error=str(exc)[:300],
                    )
            elapsed = time.monotonic() - t0
            agent_tool_duration_seconds.labels(tool=name).observe(elapsed)
            new_messages.append(
                ToolMessage(
                    content=serialize_tool_result(result),
                    tool_call_id=call.get("id", "unknown"),
                    name=name,
                )
            )
        return {"messages": new_messages}

    return run_tools


_AGENT_ERROR_FALLBACK = (
    "I hit an error while thinking about that question. The system has "
    "logged the details. Please try rephrasing or breaking the question "
    "into smaller parts."
)

_LLM_MAX_RETRIES = 2  # 1 original + 2 retries = 3 total attempts
_LLM_RETRY_BACKOFF_BASE_S = 1.0  # exponential: 1s, 2s


def _retry_reason(exc: Exception) -> str:
    """Bucket the transient error for the `reason` Prometheus label."""
    msg = (str(exc) + " " + type(exc).__name__).lower()
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "503" in msg or "502" in msg or "504" in msg or "500" in msg:
        return "5xx"
    return "other"


def _log_step_success(
    response: Any, state: AgentState, t0: float, retries: int
) -> tuple[float, int]:
    from nl_engine.agent.metrics import agent_step_duration_seconds

    elapsed = time.monotonic() - t0
    agent_step_duration_seconds.observe(elapsed)
    step_n = state.step_count + 1
    tool_calls_count = len(getattr(response, "tool_calls", []) or [])
    slog.info(
        "agent.step",
        step=step_n,
        elapsed_ms=int(elapsed * 1000),
        retry_count=retries,
        has_tool_calls=tool_calls_count > 0,
        tool_call_count=tool_calls_count,
        content_len=len(str(response.content)) if response.content else 0,
    )
    return elapsed, step_n


def _record_retry(exc: Exception, attempt: int) -> float:
    from nl_engine.agent.metrics import agent_llm_retries_total

    backoff: float = _LLM_RETRY_BACKOFF_BASE_S * (2**attempt)
    reason = _retry_reason(exc)
    agent_llm_retries_total.labels(reason=reason).inc()
    slog.warning(
        "agent.llm_retry",
        attempt=attempt + 1,
        max_attempts=_LLM_MAX_RETRIES + 1,
        backoff_s=backoff,
        reason=reason,
        error=str(exc)[:200],
    )
    return backoff


def _step_failed(
    state: AgentState, t0: float, retries: int, exc: Exception | None
) -> dict[str, Any]:
    from nl_engine.agent.metrics import agent_step_duration_seconds

    elapsed = time.monotonic() - t0
    agent_step_duration_seconds.observe(elapsed)
    slog.error(
        "agent.step_failed",
        step=state.step_count + 1,
        elapsed_ms=int(elapsed * 1000),
        retries=retries,
        error_type=type(exc).__name__ if exc else "Unknown",
        error=str(exc)[:300] if exc else "",
    )
    return {
        "messages": [AIMessage(content=_AGENT_ERROR_FALLBACK)],
        "step_count": state.step_count + 1,
    }


def _make_agent_step(llm: BaseChatModel, tools: list[BaseTool]) -> Any:
    bound = llm.bind_tools(tools)
    wall_timeout = float(
        os.environ.get("AGENT_STEP_TIMEOUT_S", AGENT_STEP_DEFAULT_TIMEOUT_S)
    )

    def agent_step(state: AgentState) -> dict[str, Any]:
        if state.request_id:
            structlog.contextvars.bind_contextvars(request_id=state.request_id)
        msgs = truncate_history(ensure_system_prompt(state.messages))
        last_exc: Exception | None = None
        retries = 0
        t0 = time.monotonic()
        for attempt in range(_LLM_MAX_RETRIES + 1):
            try:
                # Per-step summary streamer: forwards `final_answer.summary`
                # token deltas to the SSE consumer registered in
                # `nl_engine.agent.streaming` (HUG-202 Phase 2).
                on_chunk = make_summary_streamer(state.request_id or "")
                response = stream_with_wall_timeout(
                    bound, msgs, wall_timeout, on_chunk
                )
                _, step_n = _log_step_success(response, state, t0, retries)
                return {"messages": [response], "step_count": step_n}
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < _LLM_MAX_RETRIES and is_transient_llm_error(exc):
                    time.sleep(_record_retry(exc, attempt))
                    retries += 1
                    continue
                break
        return _step_failed(state, t0, retries, last_exc)

    return agent_step


def _step_cap_node(state: AgentState) -> dict[str, Any]:
    from nl_engine.agent.metrics import agent_step_cap_hits_total

    if state.request_id:
        structlog.contextvars.bind_contextvars(request_id=state.request_id)
    agent_step_cap_hits_total.inc()
    slog.warning(
        "agent.step_cap_hit",
        cap=MAX_STEPS_PER_TURN,
        thread_id=state.thread_id,
    )
    return {
        "messages": [
            AIMessage(content=_STEP_CAP_MESSAGE.format(cap=MAX_STEPS_PER_TURN))
        ]
    }


# Re-exported for tests; bind_request_id keeps the contextvar import
# explicit so test setups can scope the binding.
__all__ = ["build_graph", "bind_request_id"]


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
