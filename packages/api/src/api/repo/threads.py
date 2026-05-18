"""Read/write helpers for threads + thread_messages (HUG-175).

Pure parameterized SQL (no f-strings). JSONB columns serialized via
psycopg's Jsonb adapter. Caller handles transactions.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from api.types.threads import MessageRole, Thread, ThreadMessage, ThreadSummary


def create_thread(
    session_id: str,
    db_url: str,
    title: str | None = None,
    user_id: str | None = None,
) -> Thread:
    """Create a thread. `user_id` (HUG-205) ties the thread to the
    durable localStorage identity; falls back to session_id for
    legacy clients that don't yet send X-Hughes-User."""
    effective_user_id = user_id or session_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (session_id, user_id, title)"
            " VALUES (%s, %s, %s)"
            " RETURNING thread_id, session_id, user_id, title, started_at,"
            " last_active_at, ended_at, slots",
            (session_id, effective_user_id, title),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("INSERT...RETURNING returned no row")
    return _row_to_thread(row)


def get_thread(thread_id: UUID, db_url: str) -> Thread | None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT thread_id, session_id, user_id, title, started_at,"
            " last_active_at, ended_at, slots"
            " FROM threads WHERE thread_id = %s",
            (str(thread_id),),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_thread(row)


def list_threads_for_user(
    user_id: str, db_url: str, limit: int = 20
) -> list[ThreadSummary]:
    """HUG-205: thread list filtered by durable user_id. Backfilled
    rows have user_id == session_id, so legacy callers that pass a
    session_id here still get their own threads back."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT thread_id, title, started_at, last_active_at"
            " FROM threads WHERE user_id = %s"
            " ORDER BY last_active_at DESC LIMIT %s",
            (user_id, limit),
        )
        rows = cur.fetchall()
    return [
        ThreadSummary(
            thread_id=r[0], title=r[1], started_at=r[2], last_active_at=r[3]
        )
        for r in rows
    ]


def list_threads_for_session(
    session_id: str, db_url: str, limit: int = 20
) -> list[ThreadSummary]:
    """Legacy access path kept for backwards-compat with any caller
    that hasn't moved to user_id yet (HUG-205). New code should call
    `list_threads_for_user` instead."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT thread_id, title, started_at, last_active_at"
            " FROM threads WHERE session_id = %s"
            " ORDER BY last_active_at DESC LIMIT %s",
            (session_id, limit),
        )
        rows = cur.fetchall()
    return [
        ThreadSummary(
            thread_id=r[0], title=r[1], started_at=r[2], last_active_at=r[3]
        )
        for r in rows
    ]


def update_thread_title(thread_id: UUID, title: str, db_url: str) -> bool:
    """Set a thread's title — but only if it's still NULL.

    The conditional WHERE makes title generation idempotent: if two
    concurrent fire-and-forget tasks fire for the same thread, the
    first commit wins, the second's UPDATE matches zero rows. Returns
    True if this call was the writer, False otherwise.
    """
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE threads SET title = %s"
            " WHERE thread_id = %s AND title IS NULL",
            (title, str(thread_id)),
        )
        return cur.rowcount == 1


def append_message(
    thread_id: UUID,
    role: MessageRole,
    db_url: str,
    parent_message_id: UUID | None = None,
    content: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    openui_dsl: str | None = None,
    mf_query: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    thinking_trace: list[dict[str, Any]] | None = None,
    turn_id: UUID | None = None,
) -> ThreadMessage:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO thread_messages"
            " (thread_id, parent_message_id, role, content,"
            "  tool_calls, tool_results, openui_dsl, mf_query, rows,"
            "  thinking_trace, turn_id)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " RETURNING message_id, thread_id, parent_message_id, role,"
            " content, tool_calls, tool_results, openui_dsl, mf_query,"
            " rows, thinking_trace, created_at",
            (
                str(thread_id),
                str(parent_message_id) if parent_message_id else None,
                role,
                content,
                Jsonb(tool_calls) if tool_calls is not None else None,
                Jsonb(tool_results) if tool_results is not None else None,
                openui_dsl,
                Jsonb(mf_query) if mf_query is not None else None,
                Jsonb(rows) if rows is not None else None,
                Jsonb(thinking_trace) if thinking_trace is not None else None,
                str(turn_id) if turn_id else None,
            ),
        )
        row = cur.fetchone()
        # Bump the thread's last_active_at on every append.
        cur.execute(
            "UPDATE threads SET last_active_at = NOW() WHERE thread_id = %s",
            (str(thread_id),),
        )
    if row is None:
        raise RuntimeError("INSERT...RETURNING returned no row")
    return _row_to_message(row)


_MESSAGE_COLUMNS = (
    " message_id, thread_id, parent_message_id, role, content,"
    " tool_calls, tool_results, openui_dsl, mf_query, rows,"
    " thinking_trace, created_at"
)


def latest_n_messages(
    thread_id: UUID, n: int, db_url: str
) -> list[ThreadMessage]:
    """Return the most-recent N messages for a thread, oldest-first."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT * FROM (SELECT{_MESSAGE_COLUMNS}"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql
            " FROM thread_messages WHERE thread_id = %s"
            " ORDER BY created_at DESC LIMIT %s"
            ") AS recent ORDER BY created_at ASC",
            (str(thread_id), n),
        )
        rows = cur.fetchall()
    return [_row_to_message(r) for r in rows]


def list_messages(thread_id: UUID, db_url: str) -> list[ThreadMessage]:
    """All messages for a thread in chronological order."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT{_MESSAGE_COLUMNS} FROM thread_messages"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql
            " WHERE thread_id = %s ORDER BY created_at ASC",
            (str(thread_id),),
        )
        rows = cur.fetchall()
    return [_row_to_message(r) for r in rows]


def _row_to_thread(row: tuple[Any, ...]) -> Thread:
    return Thread(
        thread_id=row[0],
        session_id=row[1],
        user_id=row[2],
        title=row[3],
        started_at=row[4],
        last_active_at=row[5],
        ended_at=row[6],
        slots=_decode_jsonb(row[7]) or {},
    )


def _row_to_message(row: tuple[Any, ...]) -> ThreadMessage:
    return ThreadMessage(
        message_id=row[0],
        thread_id=row[1],
        parent_message_id=row[2],
        role=row[3],
        content=row[4],
        tool_calls=_decode_jsonb(row[5]),
        tool_results=_decode_jsonb(row[6]),
        openui_dsl=row[7],
        mf_query=_decode_jsonb(row[8]),
        rows=_decode_jsonb(row[9]),
        thinking_trace=_decode_jsonb(row[10]),
        created_at=row[11],
    )


def _decode_jsonb(value: Any) -> Any:
    """psycopg returns JSONB as parsed objects already, but tests sometimes
    inject raw strings. Coerce defensively."""
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def _now() -> datetime:  # pragma: no cover - pytest patches this if needed
    return datetime.utcnow()
