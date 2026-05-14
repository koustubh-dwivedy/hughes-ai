"""Schema-shape tests for migration 016 (research tables).

Verifies tables exist, indexes/constraints are in place, FK cascades
delete cleanly, the migration is idempotent, and the per-plan/per-thread
version uniqueness rules hold. Lives in the integration tier — needs a
real Postgres with `migrations/016_research_tables.sql` applied.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = _REPO_ROOT / "migrations" / "016_research_tables.sql"


def _db() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set; research-schema tests need Postgres")
    return _DB_URL


def _table_columns(table: str) -> set[str]:
    with psycopg.connect(_db()) as c, c.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s",
            (table,),
        )
        return {row[0] for row in cur.fetchall()}


def _index_exists(name: str) -> bool:
    with psycopg.connect(_db()) as c, c.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = %s",
            (name,),
        )
        return cur.fetchone() is not None


def _seed_thread(conn: psycopg.Connection) -> str:
    """Insert a throwaway thread for FK targeting; return its UUID."""
    sid = f"pytest-research-{uuid4().hex[:8]}"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (session_id) VALUES (%s)"
            " RETURNING thread_id",
            (sid,),
        )
        row = cur.fetchone()
    conn.commit()
    assert row is not None
    return str(row[0])


def test_research_plans_has_expected_columns() -> None:
    cols = _table_columns("research_plans")
    assert {
        "plan_id",
        "thread_id",
        "version",
        "status",
        "plan_json",
        "created_at",
    } <= cols


def test_research_steps_has_expected_columns() -> None:
    cols = _table_columns("research_steps")
    assert {
        "step_id",
        "plan_id",
        "ordinal",
        "description",
        "status",
        "assigned_subagent",
        "started_at",
        "completed_at",
    } <= cols


def test_research_findings_has_expected_columns() -> None:
    cols = _table_columns("research_findings")
    assert {
        "finding_id",
        "step_id",
        "summary_text",
        "structured_rows_json",
        "mf_query_json",
        "cited_artifacts",
        "created_at",
    } <= cols


def test_research_lead_notes_has_expected_columns() -> None:
    cols = _table_columns("research_lead_notes")
    assert {"note_id", "plan_id", "version", "body_md", "created_at"} <= cols


def test_thread_version_desc_index_exists() -> None:
    """The dominant access pattern is `get_latest_plan` which sorts
    by (thread_id, version DESC). The plan calls this index out by
    name; pin it so a future refactor doesn't drop it silently."""
    assert _index_exists("idx_research_plans_thread_version")


def _seed_full_chain(conn: psycopg.Connection, thread_id: str) -> dict[str, str]:
    """Insert one row in each research_* table tied to `thread_id`.
    Returns a dict of the four ids, keyed by table name."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO research_plans (thread_id, version, status, plan_json)"
            " VALUES (%s, 1, 'draft', %s) RETURNING plan_id",
            (thread_id, json.dumps({"steps": []})),
        )
        plan_id = str(cur.fetchone()[0])  # type: ignore[index]
        cur.execute(
            "INSERT INTO research_steps (plan_id, ordinal, description, status)"
            " VALUES (%s, 1, 'fetch metrics', 'pending') RETURNING step_id",
            (plan_id,),
        )
        step_id = str(cur.fetchone()[0])  # type: ignore[index]
        cur.execute(
            "INSERT INTO research_findings (step_id, summary_text)"
            " VALUES (%s, 'demo finding') RETURNING finding_id",
            (step_id,),
        )
        finding_id = str(cur.fetchone()[0])  # type: ignore[index]
        cur.execute(
            "INSERT INTO research_lead_notes (plan_id, version, body_md)"
            " VALUES (%s, 1, 'demo note') RETURNING note_id",
            (plan_id,),
        )
        note_id = str(cur.fetchone()[0])  # type: ignore[index]
    conn.commit()
    return {
        "research_plans": plan_id,
        "research_steps": step_id,
        "research_findings": finding_id,
        "research_lead_notes": note_id,
    }


_PK_COL = {
    "research_plans": "plan_id",
    "research_steps": "step_id",
    "research_findings": "finding_id",
    "research_lead_notes": "note_id",
}


def _row_exists(conn: psycopg.Connection, table: str, pk: str) -> bool:
    col = _PK_COL[table]
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {table} WHERE {col} = %s",  # noqa: S608 — literals
            (pk,),
        )
        return cur.fetchone() is not None


def test_cascade_thread_to_plan_to_step_to_finding_to_note() -> None:
    """Deleting a thread must take its plans, steps, findings, and
    lead notes with it — otherwise orphans accumulate."""
    with psycopg.connect(_db()) as conn:
        thread_id = _seed_thread(conn)
        ids = _seed_full_chain(conn, thread_id)
        for table, pk in ids.items():
            assert _row_exists(conn, table, pk), f"setup row missing in {table}"
        with conn.cursor() as cur:
            cur.execute("DELETE FROM threads WHERE thread_id = %s", (thread_id,))
        conn.commit()
        for table, pk in ids.items():
            assert not _row_exists(conn, table, pk), (
                f"{table} row survived parent-thread delete"
            )


def test_unique_thread_id_version_rejects_duplicates() -> None:
    """The plan-version uniqueness constraint is load-bearing — re-plans
    rely on `version+=1` succeeding only when there's no collision."""
    insert_sql = (
        "INSERT INTO research_plans (thread_id, version, status, plan_json)"
        " VALUES (%s, 1, 'draft', '{}'::jsonb)"
    )
    with psycopg.connect(_db()) as conn:
        thread_id = _seed_thread(conn)
        with conn.cursor() as cur:
            cur.execute(insert_sql, (thread_id,))
        conn.commit()
        with pytest.raises(psycopg.errors.UniqueViolation), conn.cursor() as cur:
            cur.execute(insert_sql, (thread_id,))
            conn.commit()
        conn.rollback()


def test_status_check_rejects_unknown_value() -> None:
    """Status enum is enforced as a CHECK constraint — unknown values
    must be rejected at write time, not silently accepted."""
    insert_sql = (
        "INSERT INTO research_plans (thread_id, version, status, plan_json)"
        " VALUES (%s, 1, 'banana', '{}'::jsonb)"
    )
    with psycopg.connect(_db()) as conn:
        thread_id = _seed_thread(conn)
        with pytest.raises(psycopg.errors.CheckViolation), conn.cursor() as cur:
            cur.execute(insert_sql, (thread_id,))
            conn.commit()
        conn.rollback()


def test_migration_is_idempotent() -> None:
    """Re-applying the migration must succeed without errors — the plan
    requires no down-migration; CI applies all migrations in order on
    every run, so non-idempotent DDL would break clean rebuilds."""
    sql = _MIGRATION.read_text()
    with psycopg.connect(_db()) as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
        cur.execute(sql)  # second pass; relations exist, IF NOT EXISTS kicks in
        conn.commit()
