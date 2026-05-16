"""Fix C — write_memory + read_memory resolve plan_id dynamically.

E2E verification (2026-05-17) found that the placeholder uuid4() plan_id
in lead_agent.stream_lead_turn's bind_memory_context call never matched
a real research_plans row, causing every write_memory call to fail with
a ForeignKeyViolation. The memory tools are silently broken in the
integrated lead-agent path.

Fix: memory tools resolve the current plan_id from thread_id via
get_latest_plan_id(thread_id, db_url) at call time. If no plan exists,
write returns a clear error; read returns body=None.

Tests:
- write_memory after propose_plan: writes succeed, row in research_lead_notes.
- write_memory before any plan exists: returns error 'no_plan_for_thread'.
- read_memory after write: returns the body.
- read_memory before plan exists: returns body=None (no error).
- Multiple writes under same key increment version.
- thread_id from contextvar is the resolution key (not the placeholder plan_id).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import psycopg
import pytest
from nl_engine.agent.memory_context import (
    bind_memory_context,
    reset_memory_context,
)
from nl_engine.agent.memory_tools import read_memory, write_memory

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    """Throwaway thread; teardown removes all rows."""
    url = _db_url()
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id, title)"
            " VALUES (gen_random_uuid(), %s, 'fixc-user', 'fixc')"
            " RETURNING thread_id",
            (f"fixc-{uuid4().hex[:8]}",),
        )
        row = cur.fetchone()
        assert row is not None  # noqa: S101 — test invariant
        tid = UUID(str(row[0]))
    try:
        yield tid
    finally:
        with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
            # Cleanup: child rows first per FK ordering.
            cur.execute(
                "DELETE FROM research_lead_notes WHERE plan_id IN"
                " (SELECT plan_id FROM research_plans WHERE thread_id = %s)",
                (str(tid),),
            )
            cur.execute(
                "DELETE FROM subagent_calls WHERE thread_id = %s", (str(tid),)
            )
            cur.execute(
                "DELETE FROM research_plans WHERE thread_id = %s", (str(tid),)
            )
            cur.execute("DELETE FROM thread_messages WHERE thread_id = %s", (str(tid),))
            cur.execute("DELETE FROM threads WHERE thread_id = %s", (str(tid),))


def _create_plan_for_thread(tid: UUID) -> UUID:
    """Insert a proposed plan for the given thread; return its plan_id."""
    with psycopg.connect(_db_url(), autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO research_plans (thread_id, version, status, plan_json)"
            " VALUES (%s, 1, 'proposed', '{}'::jsonb)"
            " RETURNING plan_id",
            (str(tid),),
        )
        row = cur.fetchone()
        assert row is not None  # noqa: S101 — test invariant
    return UUID(str(row[0]))


def _bind(tid: UUID):
    """Bind memory context the way the lead-agent runner does — with a
    placeholder plan_id that DOESN'T reference a real plan. The fix
    must work despite this; tools resolve plan_id from thread_id."""
    return bind_memory_context(uuid4(), _db_url(), thread_id=tid)


# ── write_memory ────────────────────────────────────────────────────


def test_write_memory_succeeds_after_propose_plan(thread_id: UUID) -> None:
    """The bug case: write_memory after propose_plan must succeed."""
    plan_id = _create_plan_for_thread(thread_id)
    tokens = _bind(thread_id)
    try:
        result = write_memory.invoke({"key": "after_step_1", "body": "branches A,B,D"})
    finally:
        reset_memory_context(tokens)
    assert "error" not in result, f"expected success, got {result}"
    assert result["version"] == 1
    # Verify row really persisted with the real plan_id.
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT body_md FROM research_lead_notes"
            " WHERE plan_id = %s AND key = %s ORDER BY version DESC LIMIT 1",
            (str(plan_id), "after_step_1"),
        )
        row = cur.fetchone()
    assert row is not None and row[0] == "branches A,B,D"


def test_write_memory_errors_when_no_plan_exists(thread_id: UUID) -> None:
    """If the lead calls write_memory BEFORE propose_plan, return a
    clear error rather than crashing with FK violation."""
    tokens = _bind(thread_id)
    try:
        result = write_memory.invoke({"key": "premature", "body": "data"})
    finally:
        reset_memory_context(tokens)
    assert result.get("error") == "no_plan_for_thread"


def test_read_memory_returns_what_write_memory_wrote(thread_id: UUID) -> None:
    plan_id = _create_plan_for_thread(thread_id)
    tokens = _bind(thread_id)
    try:
        write_memory.invoke({"key": "k1", "body": "value-one"})
        result = read_memory.invoke({"key": "k1"})
    finally:
        reset_memory_context(tokens)
    assert result == {"body": "value-one"}
    # Plan FK confirmed.
    assert plan_id is not None


def test_read_memory_returns_none_when_no_plan_exists(thread_id: UUID) -> None:
    """Before any plan exists, read_memory returns body=None without error."""
    tokens = _bind(thread_id)
    try:
        result = read_memory.invoke({"key": "anything"})
    finally:
        reset_memory_context(tokens)
    assert result == {"body": None}


def test_write_memory_versions_increment_per_key(thread_id: UUID) -> None:
    _create_plan_for_thread(thread_id)
    tokens = _bind(thread_id)
    try:
        r1 = write_memory.invoke({"key": "k", "body": "v1"})
        r2 = write_memory.invoke({"key": "k", "body": "v2"})
        r3 = write_memory.invoke({"key": "k", "body": "v3"})
        latest = read_memory.invoke({"key": "k"})
    finally:
        reset_memory_context(tokens)
    assert r1["version"] == 1
    assert r2["version"] == 2
    assert r3["version"] == 3
    assert latest == {"body": "v3"}


def test_write_memory_uses_latest_plan_when_multiple_exist(thread_id: UUID) -> None:
    """propose_plan supersedes earlier versions. Memory should bind to
    the latest plan (highest version) so notes follow the active plan."""
    plan1 = _create_plan_for_thread(thread_id)
    # Mark plan1 superseded and add a plan2 — the propose_plan flow.
    with psycopg.connect(_db_url(), autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE research_plans SET status='superseded' WHERE plan_id = %s",
            (str(plan1),),
        )
        cur.execute(
            "INSERT INTO research_plans (thread_id, version, status, plan_json)"
            " VALUES (%s, 2, 'proposed', '{}'::jsonb) RETURNING plan_id",
            (str(thread_id),),
        )
        row = cur.fetchone()
        plan2 = UUID(str(row[0])) if row else None
    assert plan2 is not None
    tokens = _bind(thread_id)
    try:
        write_memory.invoke({"key": "k", "body": "binds to plan2"})
    finally:
        reset_memory_context(tokens)
    # Note row should be under plan2, not plan1.
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT plan_id FROM research_lead_notes WHERE key = 'k'"
            " AND plan_id IN (%s, %s)",
            (str(plan1), str(plan2)),
        )
        plan_ids = {UUID(str(r[0])) for r in cur.fetchall()}
    assert plan_ids == {plan2}, f"expected {{plan2}}, got {plan_ids}"
