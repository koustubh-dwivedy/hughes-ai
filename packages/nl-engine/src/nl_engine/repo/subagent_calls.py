"""Subagent invocation audit log (HUG-243).

One row per `run_subagent` call by the lead. The lead's tool body
inserts a `pending` row, transitions through `running` to either
`complete` (with final_answer payload) or `failed` (with error text).

The frontend's `SubagentCallList` (HUG-245) renders these rows live via
SSE event invalidation; the audit panel reads them post-hoc.
"""

from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


class CallRow(NamedTuple):
    call_id: UUID
    thread_id: UUID
    plan_id: UUID | None
    plan_step_ordinal: int | None
    prompt: str
    status: str


def insert_pending(
    thread_id: UUID,
    plan_id: UUID | None,
    prompt: str,
    plan_step_ordinal: int | None,
    db_url: str,
    parent_message_id: UUID | None = None,
) -> UUID:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO subagent_calls"
            " (thread_id, plan_id, prompt, plan_step_ordinal,"
            " parent_message_id, status)"
            " VALUES (%s, %s, %s, %s, %s, 'pending')"
            " RETURNING call_id",
            (
                str(thread_id),
                str(plan_id) if plan_id else None,
                prompt,
                plan_step_ordinal,
                str(parent_message_id) if parent_message_id else None,
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("subagent_calls INSERT...RETURNING returned no row")
    return UUID(str(row[0]))


def mark_running(call_id: UUID, db_url: str) -> None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE subagent_calls SET status = 'running'"
            " WHERE call_id = %s",
            (str(call_id),),
        )


def mark_complete(
    call_id: UUID,
    summary: str | None,
    rows: list[dict[str, Any]] | None,
    mf_query: dict[str, Any] | None,
    db_url: str,
) -> None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE subagent_calls SET"
            " status = 'complete',"
            " summary_text = %s,"
            " rows_json = %s,"
            " mf_query_json = %s,"
            " completed_at = NOW()"
            " WHERE call_id = %s",
            (
                summary,
                Jsonb(rows) if rows is not None else None,
                Jsonb(mf_query) if mf_query is not None else None,
                str(call_id),
            ),
        )


def mark_failed(call_id: UUID, error_text: str, db_url: str) -> None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE subagent_calls SET"
            " status = 'failed',"
            " error_text = %s,"
            " completed_at = NOW()"
            " WHERE call_id = %s",
            (error_text, str(call_id)),
        )


def get_call(call_id: UUID, db_url: str) -> dict[str, Any] | None:
    """Lookup helper for tests + the audit GET endpoint (HUG-245)."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT call_id, thread_id, plan_id, plan_step_ordinal,"
            " prompt, status, summary_text, rows_json, mf_query_json,"
            " error_text, started_at, completed_at"
            " FROM subagent_calls WHERE call_id = %s",
            (str(call_id),),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "call_id": UUID(str(row[0])),
        "thread_id": UUID(str(row[1])),
        "plan_id": UUID(str(row[2])) if row[2] else None,
        "plan_step_ordinal": row[3],
        "prompt": row[4],
        "status": row[5],
        "summary_text": row[6],
        "rows_json": row[7],
        "mf_query_json": row[8],
        "error_text": row[9],
        "started_at": row[10],
        "completed_at": row[11],
    }
