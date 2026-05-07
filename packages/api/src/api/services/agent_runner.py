"""Run a user turn through the LangGraph agent + emit SSE events.

The graph is sync; we run it in a thread so the event loop isn't
blocked by LLM latency. Persists every canonical message as it streams.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import structlog.contextvars
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from nl_engine.agent.graph import build_graph
from nl_engine.agent.persistence import to_canonical
from nl_engine.agent.state import AgentState
from nl_engine.logging import bind_request_id, get_logger

from api.prometheus import (
    agent_error_frames_total,
    agent_steps_per_turn,
    agent_turn_duration_seconds,
)
from api.repo import threads as threads_repo
from api.services.agent_runner_events import (
    emit_step,
    emit_thinking,
    terminal_payload,
)
from api.services.openui_validator import validate_openui_dsl
from api.types.threads import ThreadMessage
from api.types.threads_api import StreamError, StreamFinal

slog = get_logger().bind(component="agent.runner")


class _PRODUCER_ERROR_SENTINEL:  # noqa: N801 — internal sentinel
    """Queue marker for graph.stream crashes; consumer emits an SSE
    `event: error` frame so the stream stays well-formed."""

    def __init__(self, message: str) -> None:
        self.message = message


log = logging.getLogger(__name__)


def _persist_assistant(thread_id: UUID, msg: AIMessage, db_url: str) -> ThreadMessage:
    canonical = to_canonical(msg)
    return threads_repo.append_message(
        thread_id=thread_id,
        role="assistant",
        db_url=db_url,
        content=canonical.get("content") or "",
        tool_calls=canonical.get("tool_calls"),
    )


def _persist_tool(
    thread_id: UUID,
    msg: ToolMessage,
    db_url: str,
    terminal: dict[str, Any] | None = None,
) -> ThreadMessage:
    """Persist a tool message. When `terminal` is the decoded
    `final_answer` payload, also propagate the rich fields (openui_dsl,
    mf_query, rows) into their dedicated columns so reloading a thread
    via GET /threads/:id renders with full fidelity instead of forcing
    the frontend to re-parse the content blob (HUG-179)."""
    canonical = to_canonical(msg)
    extra: dict[str, Any] = {}
    if terminal is not None:
        dsl = terminal.get("openui_dsl")
        if isinstance(dsl, str) and dsl:
            extra["openui_dsl"] = dsl
        mf = terminal.get("mf_query")
        if isinstance(mf, dict):
            extra["mf_query"] = mf
        rows = terminal.get("rows")
        if isinstance(rows, list):
            extra["rows"] = rows
    return threads_repo.append_message(
        thread_id=thread_id,
        role="tool",
        db_url=db_url,
        content=canonical.get("content") or "",
        tool_results=canonical.get("tool_results"),
        **extra,
    )


def _make_producer(graph: Any, initial: AgentState, queue: asyncio.Queue[Any]) -> Any:
    """Build the producer thread function. Crashes are converted into
    a sentinel placed on the queue so the consumer can yield an SSE
    error frame instead of silently breaking the stream (HUG-190 Phase C)."""

    def producer() -> None:
        try:
            for chunk in graph.stream(initial, stream_mode="values"):
                queue.put_nowait(chunk)
        except Exception as exc:  # noqa: BLE001 — surfaced as SSE error frame
            log.warning(
                "agent_runner producer crashed (%s): %s",
                type(exc).__name__,
                str(exc)[:300],
            )
            queue.put_nowait(_PRODUCER_ERROR_SENTINEL(message=str(exc)[:300]))
        finally:
            queue.put_nowait(None)

    return producer


def _start_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str,
) -> tuple[Any, asyncio.Queue[Any]]:
    token = bind_request_id(request_id) if request_id else None
    structlog.contextvars.bind_contextvars(
        request_id=request_id, thread_id=str(thread_id)
    )
    slog.info(
        "agent.turn_started",
        thread_id=str(thread_id),
        history_len=len(history),
        user_content_len=len(user_content),
    )
    threads_repo.append_message(
        thread_id=thread_id, role="user", db_url=db_url, content=user_content
    )
    initial = _build_initial_state(thread_id, user_content, history, request_id)
    queue: asyncio.Queue[Any] = asyncio.Queue()
    asyncio.create_task(
        asyncio.to_thread(_make_producer(build_graph(llm), initial, queue))
    )
    return token, queue


def _emit_error_frame(message: str) -> dict[str, Any]:
    agent_error_frames_total.inc()
    slog.warning("agent.error_frame_emitted", error=message[:300])
    return {
        "event": "error",
        "data": StreamError(message=message).model_dump_json(),
    }


async def stream_user_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Persist the user message, run the agent, yield SSE events.

    `request_id` is bound into structlog contextvars + AgentState so
    every log line + downstream node carries it.
    """
    token, queue = _start_turn(
        thread_id, user_content, db_url, llm, history, request_id
    )
    turn_start = time.monotonic()
    seen: set[int] = set()
    step_idx = 0
    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if isinstance(chunk, _PRODUCER_ERROR_SENTINEL):
                yield _emit_error_frame(chunk.message)
                continue
            for msg in chunk.get("messages", []):
                if id(msg) in seen or isinstance(msg, HumanMessage):
                    seen.add(id(msg))
                    continue
                seen.add(id(msg))
                step_idx += 1
                for event in _process_message(msg, step_idx, thread_id, db_url):
                    yield event
    finally:
        _finalize_turn(thread_id, turn_start, step_idx, token)


def _finalize_turn(
    thread_id: UUID, turn_start: float, step_idx: int, token: Any
) -> None:
    elapsed = time.monotonic() - turn_start
    agent_turn_duration_seconds.observe(elapsed)
    agent_steps_per_turn.observe(step_idx)
    slog.info(
        "agent.turn_completed",
        thread_id=str(thread_id),
        elapsed_ms=int(elapsed * 1000),
        steps=step_idx,
    )
    structlog.contextvars.unbind_contextvars("request_id", "thread_id")
    if token is not None:
        from nl_engine.logging import _request_id  # noqa: PLC0415

        _request_id.reset(token)


def _process_message(
    msg: Any, step_idx: int, thread_id: UUID, db_url: str
) -> list[dict[str, Any]]:
    """Per-message side effects: persist + emit thinking/step/final."""
    out: list[dict[str, Any]] = []
    thinking = emit_thinking(msg, step_idx)
    if thinking is not None:
        slog.info("agent.narration_emitted", step=step_idx, msg_kind=type(msg).__name__)
        out.append(thinking)
    step_event = emit_step(msg, step_idx)
    if step_event is not None:
        out.append(step_event)
    if isinstance(msg, AIMessage):
        _persist_assistant(thread_id, msg, db_url)
    elif isinstance(msg, ToolMessage):
        terminal = terminal_payload(msg)
        persisted = _persist_tool(thread_id, msg, db_url, terminal=terminal)
        if terminal is not None:
            dsl = terminal.get("openui_dsl")
            openui = validate_openui_dsl(dsl) if isinstance(dsl, str) and dsl else None
            out.append(
                {
                    "event": "final",
                    "data": StreamFinal(
                        message=persisted, openui=openui
                    ).model_dump_json(),
                }
            )
    return out


def _build_initial_state(
    thread_id: UUID,
    user_content: str,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AgentState:
    """Assemble the message list passed to the graph: prior messages
    (recovered from thread_messages) + the new user message."""
    from nl_engine.agent.persistence import from_canonical

    prior = [
        from_canonical(
            {
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_results": m.tool_results,
            }
        )
        for m in history
        if m.role in {"user", "assistant", "tool", "system"}
    ]
    prior.append(HumanMessage(content=user_content))
    return AgentState(
        messages=prior,
        thread_id=str(thread_id),
        request_id=request_id,
    )


