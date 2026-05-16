"""Lead-agent memory tests (HUG-241).

Covers:
- `read_lead_note_by_key` returns the LATEST body for a `(plan_id, key)`.
- `read_lead_note_by_key` returns None when nothing has been written.
- `write_lead_note` truncates bodies over `MAX_NOTE_CHARS`.
- The `read_memory` / `write_memory` LangChain @tool functions correctly
  resolve plan_id + db_url from the context binding, and return clear
  error dicts when no context is bound.

Uses live Postgres (matches the api `pytest.mark.db` pattern).
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import psycopg
import pytest
from nl_engine.agent.memory_context import (
    bind_memory_context,
    reset_memory_context,
)
from nl_engine.agent.tools import read_memory, write_memory
from nl_engine.repo.lead_memory import (
    MAX_NOTE_CHARS,
    read_lead_note_by_key,
    write_lead_note,
)

pytestmark = pytest.mark.db  # CI integration-test job

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def plan_id() -> UUID:
    """Create a throwaway thread + plan, yield the plan_id, clean up."""
    url = _db_url()
    pid = uuid4()
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id, title)"
            " VALUES (gen_random_uuid(), 'memtest', 'memtest', 'mem')"
            " RETURNING thread_id"
        )
        row = cur.fetchone()
        assert row is not None
        tid = row[0]
        cur.execute(
            "INSERT INTO research_plans"
            " (plan_id, thread_id, version, status, plan_json)"
            " VALUES (%s, %s, 1, 'proposed', '{}'::jsonb)",
            (str(pid), tid),
        )
    try:
        yield pid
    finally:
        with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM threads WHERE session_id = 'memtest'")


def test_read_memory_returns_latest(plan_id: UUID) -> None:
    url = _db_url()
    write_lead_note(plan_id, "after_step_1", "first", url)
    write_lead_note(plan_id, "after_step_1", "second", url)
    write_lead_note(plan_id, "after_step_1", "third", url)
    body = read_lead_note_by_key(plan_id, "after_step_1", url)
    assert body == "third"


def test_read_memory_returns_none_when_missing(plan_id: UUID) -> None:
    url = _db_url()
    assert read_lead_note_by_key(plan_id, "never_written", url) is None


def test_write_memory_truncates_over_cap(plan_id: UUID) -> None:
    url = _db_url()
    body = "x" * (MAX_NOTE_CHARS + 1000)
    result = write_lead_note(plan_id, "huge", body, url)
    assert result.truncated is True
    assert len(result.body) == MAX_NOTE_CHARS
    # Round-trips through the DB as the truncated form.
    stored = read_lead_note_by_key(plan_id, "huge", url)
    assert stored is not None
    assert len(stored) == MAX_NOTE_CHARS


def test_distinct_keys_are_independent(plan_id: UUID) -> None:
    url = _db_url()
    write_lead_note(plan_id, "a", "value-a", url)
    write_lead_note(plan_id, "b", "value-b", url)
    assert read_lead_note_by_key(plan_id, "a", url) == "value-a"
    assert read_lead_note_by_key(plan_id, "b", url) == "value-b"


# ── @tool function tests (with context binding) ──────────────────────


def test_read_memory_tool_returns_stored_body(plan_id: UUID) -> None:
    url = _db_url()
    write_lead_note(plan_id, "foo", "hello-world", url)
    tokens = bind_memory_context(plan_id, url)
    try:
        result = read_memory.invoke({"key": "foo"})
    finally:
        reset_memory_context(tokens)
    assert result == {"body": "hello-world"}


def test_read_memory_tool_returns_none_on_missing(plan_id: UUID) -> None:
    tokens = bind_memory_context(plan_id, _db_url())
    try:
        result = read_memory.invoke({"key": "missing"})
    finally:
        reset_memory_context(tokens)
    assert result == {"body": None}


def test_read_memory_tool_errors_when_unbound() -> None:
    """No context bound → tool returns error dict, doesn't crash."""
    result = read_memory.invoke({"key": "foo"})
    assert result == {"body": None, "error": "memory_context_not_bound"}


def test_write_memory_tool_persists_and_reports(plan_id: UUID) -> None:
    url = _db_url()
    tokens = bind_memory_context(plan_id, url)
    try:
        result = write_memory.invoke({"key": "k1", "body": "v1"})
    finally:
        reset_memory_context(tokens)
    assert result == {"version": 1, "truncated": False, "stored_chars": 2}
    assert read_lead_note_by_key(plan_id, "k1", url) == "v1"


def test_write_memory_tool_truncates(plan_id: UUID) -> None:
    url = _db_url()
    huge = "y" * (MAX_NOTE_CHARS + 500)
    tokens = bind_memory_context(plan_id, url)
    try:
        result = write_memory.invoke({"key": "big", "body": huge})
    finally:
        reset_memory_context(tokens)
    assert result["truncated"] is True
    assert result["stored_chars"] == MAX_NOTE_CHARS


def test_write_memory_tool_errors_when_unbound() -> None:
    result = write_memory.invoke({"key": "k", "body": "v"})
    assert result == {"error": "memory_context_not_bound"}
