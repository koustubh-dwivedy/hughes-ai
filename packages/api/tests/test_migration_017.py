"""Migration 017 (HUG-241): apply, re-apply, verify columns/FKs/indexes."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")
_MIGRATION = (
    Path(__file__).resolve().parents[3] / "migrations" / "017_lead_agent_schema.sql"
)


def _apply() -> None:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    sql = _MIGRATION.read_text()
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(sql)


def test_migration_applies_cleanly() -> None:
    """First apply succeeds. (Second apply tested separately.)"""
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()


def test_migration_is_idempotent() -> None:
    """Re-applying the migration on top of itself doesn't raise."""
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()
    _apply()  # second apply must not raise


def test_subagent_calls_columns_present() -> None:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()
    expected = {
        "call_id",
        "thread_id",
        "plan_id",
        "parent_message_id",
        "plan_step_ordinal",
        "prompt",
        "status",
        "summary_text",
        "rows_json",
        "mf_query_json",
        "error_text",
        "started_at",
        "completed_at",
    }
    with psycopg.connect(_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'subagent_calls'"
        )
        actual = {row[0] for row in cur.fetchall()}
    missing = expected - actual
    assert not missing, f"missing columns: {missing}"


def test_subagent_calls_indexes_present() -> None:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()
    expected = {
        "idx_subagent_calls_thread_status",
        "idx_subagent_calls_plan",
    }
    with psycopg.connect(_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'subagent_calls'"
        )
        actual = {row[0] for row in cur.fetchall()}
    missing = expected - actual
    assert not missing, f"missing indexes: {missing}"


def test_thread_messages_plan_id_present() -> None:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()
    with psycopg.connect(_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'thread_messages' AND column_name = 'plan_id'"
        )
        assert cur.fetchone() is not None


def test_research_lead_notes_key_column_present() -> None:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()
    with psycopg.connect(_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'research_lead_notes' AND column_name = 'key'"
        )
        assert cur.fetchone() is not None


def test_research_plans_accepts_proposed_status() -> None:
    """Inserting a plan with status='proposed' must succeed under the new check."""
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    _apply()
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        # Create a throwaway thread first (plans FK threads).
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id, title)"
            " VALUES (gen_random_uuid(), 'tmig017', 'tmig017', 'mig')"
            " RETURNING thread_id"
        )
        row = cur.fetchone()
        assert row is not None
        tid = row[0]
        try:
            cur.execute(
                "INSERT INTO research_plans (thread_id, version, status, plan_json)"
                " VALUES (%s, 1, 'proposed', '{}'::jsonb)",
                (tid,),
            )
        finally:
            cur.execute("DELETE FROM threads WHERE thread_id = %s", (tid,))
