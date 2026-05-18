"""Durable state for one agent turn (HUG-266).

A `turn_state` row is created when the user submits a query; the
agent's background asyncio task transitions it to `complete` or
`failed` when done. The reload-resume path queries this table to
decide whether to reconnect to a tail SSE stream. The lifespan startup
sweep marks any orphaned `running` rows (left over from API restarts)
as `failed`.

Writes are direct psycopg — same pattern as `subagent_calls` (HUG-243).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import psycopg


@dataclass(frozen=True)
class TurnState:
    turn_id: UUID
    thread_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    error_text: str | None
    last_seq_no: int | None


_SELECT_COLS = (
    "turn_id, thread_id, status, started_at, completed_at,"
    " error_text, last_seq_no"
)


def _row_to_obj(row: tuple[Any, ...]) -> TurnState:
    return TurnState(
        turn_id=UUID(str(row[0])),
        thread_id=UUID(str(row[1])),
        status=row[2],
        started_at=row[3],
        completed_at=row[4],
        error_text=row[5],
        last_seq_no=row[6],
    )


def create_running(thread_id: UUID, db_url: str) -> UUID:
    """Insert a fresh `running` row; return its turn_id."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO turn_state (thread_id, status)"
            " VALUES (%s, 'running') RETURNING turn_id",
            (str(thread_id),),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("turn_state INSERT...RETURNING returned no row")
    return UUID(str(row[0]))


def mark_complete(turn_id: UUID, last_seq_no: int | None, db_url: str) -> None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE turn_state SET status='complete',"
            " completed_at=NOW(), last_seq_no=%s"
            " WHERE turn_id=%s AND status='running'",
            (last_seq_no, str(turn_id)),
        )


def mark_failed(turn_id: UUID, error_text: str, db_url: str) -> None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE turn_state SET status='failed',"
            " completed_at=NOW(), error_text=%s"
            " WHERE turn_id=%s AND status='running'",
            (error_text[:1000], str(turn_id)),
        )


def get_running_for_thread(
    thread_id: UUID, db_url: str
) -> TurnState | None:
    """Return the currently-running turn for this thread, if any.

    Used by `start_lead_turn` for the double-submit guard and by the
    reload-resume frontend probe. Partial index makes this O(1)-ish.
    """
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_SELECT_COLS} FROM turn_state"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal col list
            " WHERE thread_id=%s AND status='running'"
            " ORDER BY started_at DESC LIMIT 1",
            (str(thread_id),),
        )
        row = cur.fetchone()
    return _row_to_obj(row) if row else None


def get_by_id(turn_id: UUID, db_url: str) -> TurnState | None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_SELECT_COLS} FROM turn_state WHERE turn_id=%s",  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal col list
            (str(turn_id),),
        )
        row = cur.fetchone()
    return _row_to_obj(row) if row else None


def cleanup_stale(db_url: str, max_age: timedelta) -> int:
    """Mark `running` rows older than `max_age` as `failed`. Run at
    API lifespan startup to recover from previous-instance crashes.
    Returns the number of rows cleaned (for telemetry)."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE turn_state SET status='failed',"
            " completed_at=NOW(),"
            " error_text='orphaned at API restart — turn lost'"
            " WHERE status='running'"
            " AND started_at < NOW() - %s",
            (max_age,),
        )
        return cur.rowcount or 0
