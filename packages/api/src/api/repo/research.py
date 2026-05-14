"""Plan + lead-note CRUD for the deep-research feature (HUG-203).

Backs migration 016. Pure parameterized SQL, JSONB via psycopg's
`Jsonb` adapter. Mirrors `repo/threads.py`.

Sibling `repo/research_steps.py` holds step + finding CRUD; split
to keep each module under the 300-line structural cap. Tests
import each module directly.

Telemetry: every public function emits `repo.research.<op>` via
`_timed`. Counters live in F5 (HUG-207).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from api.logging import get_logger
from api.types.research import LeadNote, Plan, PlanStatus

_log = get_logger().bind(component="repo.research")


@contextmanager
def _timed(op: str) -> Iterator[None]:
    """Emit `repo.research.<op>` with timing on exit. Exposed for
    `repo/research_steps.py` to share so both modules emit
    consistently-shaped structlog events."""
    start = time.perf_counter()
    try:
        yield
    finally:
        _log.info(
            f"repo.research.{op}",
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )


def _scalar_int(row: tuple[Any, ...] | None) -> int:
    if row is None:
        raise RuntimeError("scalar query returned no row")
    return int(row[0])


# ---- plans ---------------------------------------------------------

_PLAN_COLS = "plan_id, thread_id, version, status, plan_json, created_at"


def _row_to_plan(row: tuple[Any, ...]) -> Plan:
    return Plan(
        plan_id=row[0],
        thread_id=row[1],
        version=row[2],
        status=row[3],
        plan_json=row[4] if row[4] is not None else {},
        created_at=row[5],
    )


def create_plan(
    thread_id: UUID,
    plan_json: dict[str, Any],
    db_url: str,
    *,
    status: PlanStatus = "draft",
    version: int | None = None,
) -> Plan:
    """Insert a new plan version. If `version` is None, picks
    `max(version)+1` (or 1) for the thread. Re-plan callers should
    pass `version` explicitly to avoid the SELECT→INSERT race."""
    with (
        _timed("create_plan"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        if version is None:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM research_plans"
                " WHERE thread_id = %s",
                (str(thread_id),),
            )
            version = _scalar_int(cur.fetchone())
        cur.execute(
            "INSERT INTO research_plans (thread_id, version, status, plan_json)"  # noqa: S608  # nosec B608 — literal column list
            " VALUES (%s, %s, %s, %s)"
            f" RETURNING {_PLAN_COLS}",
            (str(thread_id), version, status, Jsonb(plan_json)),
        )
        out = cur.fetchone()
    if out is None:
        raise RuntimeError("INSERT...RETURNING returned no row")
    return _row_to_plan(out)


def get_latest_plan(thread_id: UUID, db_url: str) -> Plan | None:
    """Highest-version plan for a thread; None if none exists. Uses
    `idx_research_plans_thread_version`."""
    with (
        _timed("get_latest_plan"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {_PLAN_COLS} FROM research_plans"  # noqa: S608  # nosec B608 — literal column list
            " WHERE thread_id = %s ORDER BY version DESC LIMIT 1",
            (str(thread_id),),
        )
        row = cur.fetchone()
    return _row_to_plan(row) if row is not None else None


def list_plan_versions(thread_id: UUID, db_url: str) -> list[Plan]:
    """All plan versions for a thread, newest-first."""
    with (
        _timed("list_plan_versions"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {_PLAN_COLS} FROM research_plans"  # noqa: S608  # nosec B608 — literal
            " WHERE thread_id = %s ORDER BY version DESC",
            (str(thread_id),),
        )
        rows = cur.fetchall()
    return [_row_to_plan(r) for r in rows]


def update_plan_status(plan_id: UUID, status: PlanStatus, db_url: str) -> bool:
    """Set a plan's status. Returns True iff a row was updated."""
    with (
        _timed("update_plan_status"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "UPDATE research_plans SET status = %s WHERE plan_id = %s",
            (status, str(plan_id)),
        )
        return cur.rowcount == 1


# ---- lead notes ----------------------------------------------------

_NOTE_COLS = "note_id, plan_id, version, body_md, created_at"


def _row_to_note(row: tuple[Any, ...]) -> LeadNote:
    return LeadNote(
        note_id=row[0],
        plan_id=row[1],
        version=row[2],
        body_md=row[3],
        created_at=row[4],
    )


def append_lead_note(plan_id: UUID, body_md: str, db_url: str) -> LeadNote:
    """Append the next note version under a plan. Version is
    `max(version)+1`, computed in the same connection to avoid
    the SELECT→INSERT race window."""
    with (
        _timed("append_lead_note"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM research_lead_notes"
            " WHERE plan_id = %s",
            (str(plan_id),),
        )
        version = _scalar_int(cur.fetchone())
        cur.execute(
            "INSERT INTO research_lead_notes (plan_id, version, body_md)"  # noqa: S608  # nosec B608 — literal column list
            " VALUES (%s, %s, %s)"
            f" RETURNING {_NOTE_COLS}",
            (str(plan_id), version, body_md),
        )
        out = cur.fetchone()
    if out is None:
        raise RuntimeError("INSERT...RETURNING returned no row")
    return _row_to_note(out)


def get_latest_lead_note(plan_id: UUID, db_url: str) -> LeadNote | None:
    """Highest-version note for a plan; None if none exists."""
    with (
        _timed("get_latest_lead_note"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {_NOTE_COLS} FROM research_lead_notes"  # noqa: S608  # nosec B608 — literal
            " WHERE plan_id = %s ORDER BY version DESC LIMIT 1",
            (str(plan_id),),
        )
        row = cur.fetchone()
    return _row_to_note(row) if row is not None else None


def list_lead_notes(plan_id: UUID, db_url: str) -> list[LeadNote]:
    """All notes for a plan, newest-first."""
    with (
        _timed("list_lead_notes"),
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            f"SELECT {_NOTE_COLS} FROM research_lead_notes"  # noqa: S608  # nosec B608 — literal
            " WHERE plan_id = %s ORDER BY version DESC",
            (str(plan_id),),
        )
        rows = cur.fetchall()
    return [_row_to_note(r) for r in rows]
