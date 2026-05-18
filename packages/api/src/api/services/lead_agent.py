"""Autonomous lead-agent runner (HUG-244 + HUG-247 Phase B).

`stream_lead_turn` is the ONLY path `routes/threads.py` uses to serve
`POST /threads/{tid}/messages`. The legacy
planner/executor/synthesizer pipeline (HUG-247 Phase B) and the
`RESEARCH_LEAD_AGENT_ENABLED` feature flag have both been removed.

The lead is a single autonomous agent: it decides when to plan, when to
delegate to subagents, when to take notes, and when to synthesize. It
runs on the chat ReAct graph (`nl_engine.agent.graph.build_graph`) with
the extended `LEAD_AGENT_TOOLS` registry (propose_plan, run_subagent,
read_memory, write_memory in addition to the data tools).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import structlog.contextvars
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from nl_engine.agent.lead_agent_prompt import LEAD_AGENT_SYSTEM_PROMPT
from nl_engine.agent.memory_context import (
    bind_memory_context,
    reset_memory_context,
)
from nl_engine.agent.run_context import (
    bind_event_emitter,
    reset_event_emitter,
)
from nl_engine.agent.state import LEAD_MAX_STEPS_PER_TURN
from nl_engine.agent.tools import LEAD_AGENT_TOOLS
from nl_engine.logging import get_logger

from api.repo import threads as threads_repo
from api.repo import turn_state as turn_state_repo
from api.services.agent_runner import run_agent_isolated
from api.services.agent_runner_chat import chat_process_message
from api.services.turn_context import bind_turn_context, reset_turn_context
from api.types.threads import ThreadMessage

_slog = get_logger().bind(component="api.lead_agent")

# Firebase Hosting's `rewrites.run` enforces a hard ~60s time-to-first-byte
# ceiling. When the LLM's first response is slow (typical 10-30s, p99 60+s)
# the agent's first `event: thinking` arrives too late and Firebase 502s
# the user out. `stream_lead_turn` yields this frame *before* the LLM call so
# the client / proxy chain sees data within milliseconds. SSE clients silently
# ignore unknown event types.
_LEAD_STREAM_START: dict[str, Any] = {"event": "stream.start", "data": "{}"}


def _make_sse_emitter(events: list[dict[str, Any]]) -> Any:
    """Build an event emitter that collects SSE-shaped events into a
    list. The list is drained by `stream_lead_turn` after each agent
    step so events emitted from tools (propose_plan / run_subagent /
    write_memory) reach the SSE channel."""

    def emit(name: str, payload: dict[str, Any]) -> None:
        import json

        events.append({"event": name, "data": json.dumps(payload, default=str)})

    return emit


def start_lead_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> UUID:
    """HUG-266: fire-and-forget entry point.

    Persists the user message, creates a `turn_state` row, and schedules
    the agent to run in a background asyncio task. Returns immediately
    with the turn_id so the route can hand off to `tail_turn` for SSE.

    Double-submit guard: if a `running` turn already exists for this
    thread, returns that turn_id instead of starting a new one. The
    caller's SSE tail will reconnect to the in-flight turn.
    """
    # Persist user message first — survives reload regardless of agent fate.
    threads_repo.append_message(
        thread_id=thread_id, role="user", db_url=db_url, content=user_content,
    )
    existing = turn_state_repo.get_running_for_thread(thread_id, db_url)
    if existing is not None:
        _slog.info(
            "lead_turn.double_submit_dedup",
            thread_id=str(thread_id),
            existing_turn_id=str(existing.turn_id),
        )
        return existing.turn_id
    turn_id = turn_state_repo.create_running(thread_id, db_url)
    asyncio.create_task(
        _drain_lead_turn(
            turn_id=turn_id,
            thread_id=thread_id,
            user_content=user_content,
            db_url=db_url,
            llm=llm,
            history=history,
            request_id=request_id,
        )
    )
    return turn_id


async def _drain_lead_turn(
    *,
    turn_id: UUID,
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str,
) -> None:
    """Background task body. Binds turn_context so persist_assistant /
    persist_tool tag each row with `turn_id`. Iterates `stream_lead_turn`
    purely for its side effects (the events it yields go nowhere — the
    tail SSE reads from the DB rows instead). Marks `turn_state` on
    completion or exception."""
    turn_token = bind_turn_context(turn_id)
    try:
        async for _event in stream_lead_turn(
            thread_id=thread_id,
            user_content=user_content,
            db_url=db_url,
            llm=llm,
            history=history,
            request_id=request_id,
        ):
            pass  # side-effect only; events surface via the tail
        last_seq = _last_seq_for_turn(turn_id, db_url)
        turn_state_repo.mark_complete(turn_id, last_seq, db_url)
        _slog.info(
            "lead_turn.completed",
            turn_id=str(turn_id),
            last_seq_no=last_seq,
        )
    except Exception as exc:  # noqa: BLE001 — boundary; record then move on
        _slog.exception(
            "lead_turn.failed", turn_id=str(turn_id), error=str(exc)[:300]
        )
        turn_state_repo.mark_failed(turn_id, f"{type(exc).__name__}: {exc}", db_url)
    finally:
        reset_turn_context(turn_token)


def _last_seq_for_turn(turn_id: UUID, db_url: str) -> int | None:
    """Highest seq_no among thread_messages rows tagged with this turn."""
    import psycopg

    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(seq_no) FROM thread_messages WHERE turn_id = %s",
            (str(turn_id),),
        )
        row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else None


async def stream_lead_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Lead-agent generator. Persists agent messages to `thread_messages`
    via `chat_process_message`; events yielded are consumed either by an
    SSE producer (legacy path) or discarded by `_drain_lead_turn` (HUG-266
    fire-and-forget path, where the tail SSE reads from DB instead).

    No longer persists the user message — `start_lead_turn` does that
    upstream so the user-visible row exists before the background task
    is scheduled.
    """
    structlog.contextvars.bind_contextvars(thread_id=str(thread_id))

    yield _LEAD_STREAM_START
    pending_events: list[dict[str, Any]] = []
    emitter = _make_sse_emitter(pending_events)
    memory_tokens = bind_memory_context(uuid4(), db_url, thread_id=thread_id)
    emitter_token = bind_event_emitter(emitter)

    # Pre-pend the lead system prompt as the first message so
    # ensure_system_prompt is a no-op (it bails when message[0] is
    # already a SystemMessage).
    extras = {"_lead_agent_run": True}
    initial_messages = [SystemMessage(content=LEAD_AGENT_SYSTEM_PROMPT)]
    extras["_initial_messages"] = initial_messages  # type: ignore[assignment]

    try:
        async for event in run_agent_isolated(
            thread_id=thread_id,
            user_input=user_content,
            history=history,
            db_url=db_url,
            llm=llm,
            process_message=chat_process_message,
            max_steps=LEAD_MAX_STEPS_PER_TURN,
            request_id=request_id,
            initial_state_extras=extras,
            tools=LEAD_AGENT_TOOLS,
        ):
            # Flush any tool-emitted events before the agent's own event.
            while pending_events:
                yield pending_events.pop(0)
            yield event
        # Flush any remaining tool events on completion.
        while pending_events:
            yield pending_events.pop(0)
    finally:
        reset_event_emitter(emitter_token)
        reset_memory_context(memory_tokens)
        structlog.contextvars.unbind_contextvars("thread_id")
