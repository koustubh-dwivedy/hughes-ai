"""Step + finding CRUD for the deep-research executor (HUG-203).

Sibling of `repo/research.py` (which holds plans + lead notes).
Split to keep each file under the 300-line structural cap. The
two modules share `_timed` from `repo.research`; tests import each
module directly via `from api.repo import research, research_steps`.

Convention: `update_step_status` does NOT auto-set timestamps —
callers in the executor (E2/S2) pass them explicitly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from api.repo.research import _timed
from api.types.research import Finding, Step, StepStatus

# ---- steps ---------------------------------------------------------

_STEP_COLS = (
    "step_id, plan_id, ordinal, description, status,"
    " assigned_subagent, started_at, completed_at"
)


def _row_to_step(row: tuple[Any, ...]) -> Step:
    return Step(
        step_id=row[0],
        plan_id=row[1],
        ordinal=row[2],
        description=row[3],
        status=row[4],
        assigned_subagent=row[5],
        started_at=row[6],
        completed_at=row[7],
    )


def create_step(
    plan_id: UUID,
    ordinal: int,
    description: str,
    db_url: str,
    *,
    status: StepStatus = "pending",
    assigned_subagent: str | None = None,
) -> Step:
    """Insert a step. Ordinal is unique per plan (schema-enforced)."""
    with (
        _timed("create_step"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "INSERT INTO research_steps"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal column list
            " (plan_id, ordinal, description, status, assigned_subagent)"
            " VALUES (%s, %s, %s, %s, %s)"
            f" RETURNING {_STEP_COLS}",
            (str(plan_id), ordinal, description, status, assigned_subagent),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("INSERT...RETURNING returned no row")
    return _row_to_step(row)


def update_step_status(
    step_id: UUID,
    status: StepStatus,
    db_url: str,
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> bool:
    """Set step status. `started_at` / `completed_at` are written
    only when non-None — repo stays dumb; the executor decides
    which timestamp belongs to which transition."""
    sets = ["status = %s"]
    args: list[Any] = [status]
    if started_at is not None:
        sets.append("started_at = %s")
        args.append(started_at)
    if completed_at is not None:
        sets.append("completed_at = %s")
        args.append(completed_at)
    args.append(str(step_id))
    sql = (
        "UPDATE research_steps SET "  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — sets list is hardcoded
        + ", ".join(sets)
        + " WHERE step_id = %s"
    )
    with (
        _timed("update_step_status"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(sql, tuple(args))  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — sets list is hardcoded
        return cur.rowcount == 1


def get_steps_for_plan(plan_id: UUID, db_url: str) -> list[Step]:
    """All steps for a plan, ordinal-ascending."""
    with (
        _timed("get_steps_for_plan"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {_STEP_COLS} FROM research_steps"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal
            " WHERE plan_id = %s ORDER BY ordinal ASC",
            (str(plan_id),),
        )
        rows = cur.fetchall()
    return [_row_to_step(r) for r in rows]


# ---- findings ------------------------------------------------------

_FINDING_COLS = (
    "finding_id, step_id, summary_text, structured_rows_json,"
    " mf_query_json, cited_artifacts, created_at"
)


def _row_to_finding(row: tuple[Any, ...]) -> Finding:
    return Finding(
        finding_id=row[0],
        step_id=row[1],
        summary_text=row[2],
        structured_rows_json=row[3],
        mf_query_json=row[4],
        cited_artifacts=row[5],
        created_at=row[6],
    )


def _maybe_jsonb(value: Any) -> Jsonb | None:
    return Jsonb(value) if value is not None else None


def append_finding(
    step_id: UUID,
    db_url: str,
    *,
    summary_text: str | None = None,
    structured_rows_json: list[dict[str, Any]] | None = None,
    mf_query_json: dict[str, Any] | None = None,
    cited_artifacts: list[dict[str, Any]] | None = None,
) -> Finding:
    """Append a finding under a step. Every JSONB column is optional."""
    with (
        _timed("append_finding"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "INSERT INTO research_findings"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal column list
            " (step_id, summary_text, structured_rows_json,"
            " mf_query_json, cited_artifacts)"
            " VALUES (%s, %s, %s, %s, %s)"
            f" RETURNING {_FINDING_COLS}",
            (
                str(step_id),
                summary_text,
                _maybe_jsonb(structured_rows_json),
                _maybe_jsonb(mf_query_json),
                _maybe_jsonb(cited_artifacts),
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("INSERT...RETURNING returned no row")
    return _row_to_finding(row)


def get_findings_for_step(step_id: UUID, db_url: str) -> list[Finding]:
    """All findings under one step, ordered by created_at. Used by
    the worker wrapper (HUG-217) to look up the just-persisted finding
    after `final_answer` fires."""
    with (
        _timed("get_findings_for_step"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {_FINDING_COLS} FROM research_findings"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — literal column list
            " WHERE step_id = %s ORDER BY created_at ASC",
            (str(step_id),),
        )
        rows = cur.fetchall()
    return [_row_to_finding(r) for r in rows]


def get_findings_for_plan(plan_id: UUID, db_url: str) -> list[Finding]:
    """Findings across every step of a plan, ordered by step ordinal
    then finding created_at."""
    qualified = ", ".join(f"f.{c}" for c in _FINDING_COLS.split(", "))
    with (
        _timed("get_findings_for_plan"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {qualified}"  # noqa: S608  # nosec B608  # nosemgrep: no-fstring-sql — qualified list of literals
            " FROM research_findings f"
            " JOIN research_steps s ON s.step_id = f.step_id"
            " WHERE s.plan_id = %s"
            " ORDER BY s.ordinal ASC, f.created_at ASC",
            (str(plan_id),),
        )
        rows = cur.fetchall()
    return [_row_to_finding(r) for r in rows]
