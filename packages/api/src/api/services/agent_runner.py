"""Run a user turn through the LangGraph agent + emit SSE events.

The graph is sync; we run it in a thread so the event loop isn't
blocked by LLM latency. Persists every canonical message as it streams.

HUG-206 (F6) introduced `run_agent_isolated` — a lower-level primitive
both chat turns and deep-research worker turns share. Today's
`stream_user_turn` is now a thin shim over it; workers (S1) will be
a sibling shim. The primitive doesn't know about thread_messages or
the chat surface; persistence policy is injected via the
`process_message` callback the caller supplies.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import UUID

import structlog.contextvars
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from nl_engine.agent.graph import build_graph
from nl_engine.agent.state import MAX_STEPS_PER_TURN, AgentState
from nl_engine.agent.streaming import clear_token_sink, set_token_sink
from nl_engine.logging import bind_request_id, get_logger

from api.prometheus import (
    agent_error_frames_total,
    agent_steps_per_turn,
    agent_turn_duration_seconds,
)
from api.repo import threads as threads_repo
from api.services.agent_runner_chat import chat_process_message
from api.services.agent_runner_loop import TurnState, consume_queue
from api.services.agent_runner_producer import (
    is_error_sentinel,
    make_producer,
)
from api.types.threads import ThreadMessage
from api.types.threads_api import StreamError, StreamToken

ProcessMessageFn = Callable[
    [Any, int, UUID, str, list[dict[str, Any]]],
    list[dict[str, Any]],
]

slog = get_logger().bind(component="agent.runner")

_TOKEN_SENTINEL_KEY = "_token_delta"  # noqa: S105  # nosec B105 — queue sentinel, not a credential


def _prepare_agent_run(
    *,
    thread_id: UUID,
    user_input: str,
    history: list[ThreadMessage],
    llm: BaseChatModel,
    max_steps: int,
    request_id: str,
    initial_state_extras: dict[str, Any] | None,
) -> tuple[Any, asyncio.Queue[Any], int]:
    """Caller-agnostic per-turn setup: bind request_id, build state,
    spawn producer thread. Returns (request_id_token, queue,
    initial_history_len).

    Deliberately does NOT persist a user-message row — that's a
    chat-surface concern; `stream_user_turn` handles it before
    calling `run_agent_isolated`. Workers (S1) won't persist
    anything to thread_messages.
    """
    token = bind_request_id(request_id) if request_id else None
    structlog.contextvars.bind_contextvars(request_id=request_id)
    slog.info(
        "agent.turn_started",
        thread_id=str(thread_id),
        history_len=len(history),
        user_content_len=len(user_input),
        max_steps=max_steps,
    )
    initial = _build_initial_state(
        thread_id=thread_id,
        user_input=user_input,
        history=history,
        max_steps=max_steps,
        request_id=request_id,
        extras=initial_state_extras,
    )
    initial_history_len = len(initial.messages)
    queue: asyncio.Queue[Any] = asyncio.Queue()
    # HUG-202 Phase 2: token deltas → asyncio queue → SSE `token` frames.
    if request_id:
        loop = asyncio.get_running_loop()

        def _sink(delta: str) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait, {_TOKEN_SENTINEL_KEY: delta}
            )

        set_token_sink(request_id, _sink)
    asyncio.create_task(
        asyncio.to_thread(make_producer(build_graph(llm), initial, queue))
    )
    return token, queue, initial_history_len


def _emit_error_frame(message: str) -> dict[str, Any]:
    agent_error_frames_total.inc()
    slog.warning("agent.error_frame_emitted", error=message[:300])
    return {
        "event": "error",
        "data": StreamError(message=message).model_dump_json(),
    }


def _token_frame(delta: str) -> dict[str, Any]:
    return {
        "event": "token",
        "data": StreamToken(content_delta=delta).model_dump_json(),
    }


async def run_agent_isolated(
    *,
    thread_id: UUID,
    user_input: str,
    history: list[ThreadMessage],
    db_url: str,
    llm: BaseChatModel,
    process_message: ProcessMessageFn,
    max_steps: int = MAX_STEPS_PER_TURN,
    request_id: str = "",
    initial_state_extras: dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Lower-level agent invoker shared by chat and worker turns.

    Caller-supplied policies:
      - `process_message`: how each AIMessage / ToolMessage is
        reacted to. The chat path persists to `thread_messages`;
        worker paths (S1) persist to `research_findings`. Both
        receive `(msg, step_idx, thread_id, db_url, trace)` —
        contract preserved from the previous `consume_queue`
        signature so the loop module didn't need to change.
      - `max_steps`: per-turn cap. Defaults to today's chat cap.
        Workers will pass a tighter value.
      - `initial_state_extras`: free-form dict merged into the
        AgentState `slots` field — handy for workers that want to
        carry a `step_id` through the graph without changing the
        AgentState schema.

    This function does NOT persist a user-message row; if your
    caller wants one, persist it yourself before calling. Same for
    binding additional structlog context (e.g. `thread_id`,
    `subagent_id`) — caller's responsibility.
    """
    token, queue, initial_history_len = _prepare_agent_run(
        thread_id=thread_id,
        user_input=user_input,
        history=history,
        llm=llm,
        max_steps=max_steps,
        request_id=request_id,
        initial_state_extras=initial_state_extras,
    )
    turn_start = time.monotonic()
    state = TurnState(initial_history_len=initial_history_len)
    try:
        async for event in consume_queue(
            queue,
            state,
            thread_id,
            db_url,
            is_error_sentinel=is_error_sentinel,
            error_frame=_emit_error_frame,
            token_sentinel_key=_TOKEN_SENTINEL_KEY,
            token_frame=_token_frame,
            process_message=process_message,
        ):
            yield event
    finally:
        if request_id:
            clear_token_sink(request_id)
        slog.info(
            "agent.token_stream_summary",
            token_count=state.token_count,
            total_chars=state.token_chars,
        )
        _finalize_turn(thread_id, turn_start, state.step_idx, token)


async def stream_user_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Persist the user message, run the agent, yield chat-shaped
    SSE events. Thin shim over `run_agent_isolated` with chat-path
    defaults: chat persistence callback, full 10-step cap,
    `latest_n_messages`-style history fed in by the caller.
    """
    threads_repo.append_message(
        thread_id=thread_id, role="user", db_url=db_url, content=user_content
    )
    structlog.contextvars.bind_contextvars(thread_id=str(thread_id))
    try:
        async for event in run_agent_isolated(
            thread_id=thread_id,
            user_input=user_content,
            history=history,
            db_url=db_url,
            llm=llm,
            process_message=chat_process_message,
            max_steps=MAX_STEPS_PER_TURN,
            request_id=request_id,
        ):
            yield event
    finally:
        structlog.contextvars.unbind_contextvars("thread_id")


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


def _build_initial_state(
    *,
    thread_id: UUID,
    user_input: str,
    history: list[ThreadMessage],
    max_steps: int,
    request_id: str = "",
    extras: dict[str, Any] | None = None,
) -> AgentState:
    """Assemble the AgentState the graph receives. Prior history is
    rehydrated via `from_canonical`; the new user input is appended
    as a HumanMessage. `extras` (e.g. `step_id` for worker turns)
    lands in `slots`."""
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
    prior.append(HumanMessage(content=user_input))
    return AgentState(
        messages=prior,
        thread_id=str(thread_id),
        max_steps=max_steps,
        request_id=request_id,
        slots=extras or {},
    )


