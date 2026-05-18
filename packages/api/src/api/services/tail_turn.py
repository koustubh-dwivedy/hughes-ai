"""DB-tailing SSE producer (HUG-266).

Replaces the old SSE-driven generator path in `routes/threads.py` POST
/messages. Instead of running the agent inside the SSE generator (which
sse-starlette cancels on client disconnect, killing persistence), the
agent runs in a background asyncio task (`_drain_lead_turn`) that
persists every message to `thread_messages` with `turn_id` set. This
file's `tail_turn` is the SSE side — it polls `thread_messages` for
new rows and synthesizes the same `event: thinking` / `event: step` /
`event: final` wire format the frontend already consumes.

Disconnect-safe: if the client disconnects, `tail_turn`'s async
generator is cancelled but the background agent task is independent
and keeps writing. On reload, the SPA hits GET /threads/{tid}/tail with
its last-seen `from_seq` and a fresh tail picks up exactly where the
previous one stopped.

Polling chosen (not LISTEN/NOTIFY) for current scale — see HUG-266
plan for the architecture rationale.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
from langchain_core.messages import AIMessage, ToolMessage

from api.repo import turn_state as turn_state_repo
from api.services.agent_runner_events import (
    emit_step,
    emit_thinking,
    terminal_payload,
)
from api.services.lead_agent import _LEAD_STREAM_START
from api.services.openui_validator import validate_openui_dsl
from api.types.threads import ThreadMessage
from api.types.threads_api import StreamFinal

_POLL_IDLE_SEC = 0.5  # gap when there's nothing new to consume
_POLL_BUSY_SEC = 0.05  # gap when we just consumed and might have more

_TERMINAL_STATUSES = frozenset({"complete", "failed", "aborted"})


@dataclass(frozen=True)
class _Row:
    seq_no: int
    role: str
    content: str | None
    tool_calls: list[dict[str, Any]] | None
    tool_results: list[dict[str, Any]] | None
    openui_dsl: str | None
    mf_query: dict[str, Any] | None
    rows: list[dict[str, Any]] | None
    thinking_trace: list[dict[str, Any]] | None
    message_id: UUID
    thread_id: UUID
    created_at: Any


def _fetch_since(
    thread_id: UUID, turn_id: UUID, cursor: int, db_url: str
) -> list[_Row]:
    """Read all rows for this turn with seq_no > cursor."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT seq_no, role, content, tool_calls, tool_results,"
            " openui_dsl, mf_query, rows, thinking_trace,"
            " message_id, thread_id, created_at"
            " FROM thread_messages"
            " WHERE thread_id = %s AND turn_id = %s AND seq_no > %s"
            " ORDER BY seq_no ASC",
            (str(thread_id), str(turn_id), cursor),
        )
        return [
            _Row(
                seq_no=r[0],
                role=r[1],
                content=r[2],
                tool_calls=r[3],
                tool_results=r[4],
                openui_dsl=r[5],
                mf_query=r[6],
                rows=r[7],
                thinking_trace=r[8],
                message_id=r[9],
                thread_id=r[10],
                created_at=r[11],
            )
            for r in cur.fetchall()
        ]


def _row_to_message(row: _Row) -> Any:
    """Reconstruct a LangChain-shaped message from a persisted row so we
    can feed it back through the existing `emit_*` helpers."""
    if row.role == "assistant":
        # AIMessage needs tool_calls=[] (not None) when empty.
        return AIMessage(
            content=row.content or "", tool_calls=row.tool_calls or []
        )
    # role == "tool": content is the JSON-serialized tool result.
    name = "final_answer" if row.openui_dsl or row.mf_query or row.rows else "tool"
    return ToolMessage(
        content=row.content or "{}", name=name, tool_call_id=str(row.message_id),
    )


def _final_payload_from_row(row: _Row) -> dict[str, Any]:
    """Build StreamFinal exactly as chat_process_message would have."""
    message = ThreadMessage(
        message_id=row.message_id,
        thread_id=row.thread_id,
        parent_message_id=None,
        role=row.role,  # type: ignore[arg-type]
        content=row.content,
        tool_calls=row.tool_calls,
        tool_results=row.tool_results,
        openui_dsl=row.openui_dsl,
        mf_query=row.mf_query,
        rows=row.rows,
        thinking_trace=row.thinking_trace,
        created_at=row.created_at,
    )
    openui = validate_openui_dsl(row.openui_dsl) if row.openui_dsl else None
    payload = StreamFinal(message=message, openui=openui)
    return {"event": "final", "data": payload.model_dump_json()}


def _events_for_row(row: _Row, step_idx: int) -> list[dict[str, Any]]:
    """Translate one persisted row into 1+ SSE events. Mirrors what
    `chat_process_message` would have emitted in real time."""
    out: list[dict[str, Any]] = []
    msg = _row_to_message(row)
    thinking = emit_thinking(msg, step_idx)
    if thinking is not None:
        out.append(thinking)
    step = emit_step(msg, step_idx)
    if step is not None:
        out.append(step)
    # Terminal events: ToolMessage with final_answer payload, OR
    # AIMessage prose with empty tool_calls (HUG-265 contract).
    is_tool_terminal = (
        isinstance(msg, ToolMessage) and terminal_payload(msg) is not None
    )
    is_ai_terminal = isinstance(msg, AIMessage) and not msg.tool_calls
    if is_tool_terminal or is_ai_terminal:
        out.append(_final_payload_from_row(row))
    return out


async def tail_turn(
    thread_id: UUID,
    turn_id: UUID,
    from_seq: int,
    db_url: str,
) -> AsyncIterator[dict[str, Any]]:
    """SSE producer: poll thread_messages for new rows in this turn,
    synthesize the wire events, exit when status flips off 'running'
    after a final no-rows pass (so we don't miss the last row written
    immediately before the status flip)."""
    cursor = from_seq
    step_idx = 0
    yield _LEAD_STREAM_START
    saw_terminal_after_flip = False
    while True:
        rows = _fetch_since(thread_id, turn_id, cursor, db_url)
        for row in rows:
            step_idx += 1
            for ev in _events_for_row(row, step_idx):
                yield ev
            cursor = row.seq_no
        state = turn_state_repo.get_by_id(turn_id, db_url)
        if state is None or state.status in _TERMINAL_STATUSES:
            if saw_terminal_after_flip:
                break
            saw_terminal_after_flip = True
            # one more pass next iteration to drain anything written
            # immediately before the status flip
        await asyncio.sleep(_POLL_BUSY_SEC if rows else _POLL_IDLE_SEC)
