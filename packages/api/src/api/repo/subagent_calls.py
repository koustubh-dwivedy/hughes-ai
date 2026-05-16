"""HTTP-side subagent_calls reads for the audit panel (HUG-245).

`list_by_plan` is the only read used by the frontend's
`useGetSubagentCallsQuery`. Writes live in `nl_engine.repo.subagent_calls`
(invoked by the lead agent's `run_subagent` tool); both packages connect
to the same Postgres independently per the import-graph rules.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg

_CALL_COLS = (
    "call_id, thread_id, plan_id, plan_step_ordinal, prompt, status,"
    " summary_text, rows_json, mf_query_json, error_text,"
    " started_at, completed_at"
)


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "call_id": str(row[0]),
        "thread_id": str(row[1]),
        "plan_id": str(row[2]) if row[2] else None,
        "plan_step_ordinal": row[3],
        "prompt": row[4],
        "status": row[5],
        "summary_text": row[6],
        "rows_json": row[7],
        "mf_query_json": row[8],
        "error_text": row[9],
        "started_at": row[10].isoformat() if row[10] else None,
        "completed_at": row[11].isoformat() if row[11] else None,
    }


def list_by_plan(plan_id: UUID, db_url: str) -> list[dict[str, Any]]:
    """All subagent_calls under a plan, ordered by started_at ascending
    so the audit panel renders them in invocation order."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_CALL_COLS} FROM subagent_calls"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal col list
            " WHERE plan_id = %s ORDER BY started_at ASC",
            (str(plan_id),),
        )
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]
