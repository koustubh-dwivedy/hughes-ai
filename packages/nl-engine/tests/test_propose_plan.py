"""propose_plan tool tests (HUG-242).

Covers:
- First call creates v1 (proposed).
- Second call marks v1 superseded + inserts v2 (proposed).
- Sixth call is capped: returns error + emits `research.plan.replan_capped`.
- Drafted event emitted with the right payload shape.
- Tool returns error dict (not crash) when no agent context is bound.
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
from nl_engine.agent.plan_tool import propose_plan
from nl_engine.agent.run_context import (
    bind_event_emitter,
    reset_event_emitter,
)
from nl_engine.repo.plans import MAX_PLAN_VERSIONS

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    """Throwaway thread; cascade-cleans plans + notes on teardown."""
    url = _db_url()
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id, title)"
            " VALUES (gen_random_uuid(), 'planttest', 'planttest', 'plan')"
            " RETURNING thread_id"
        )
        row = cur.fetchone()
        assert row is not None
        tid = UUID(str(row[0]))
    try:
        yield tid
    finally:
        with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM threads WHERE session_id = 'planttest'")


@pytest.fixture
def events() -> Iterator[list[tuple[str, dict]]]:
    """Bind an event emitter that records all events into a list."""
    recorded: list[tuple[str, dict]] = []

    def emit(name: str, payload: dict) -> None:
        recorded.append((name, payload))

    token = bind_event_emitter(emit)
    try:
        yield recorded
    finally:
        reset_event_emitter(token)


def _bind(thread_id: UUID, plan_id: UUID | None = None):
    return bind_memory_context(
        plan_id or uuid4(),  # plan_id contextvar must be set; not used by propose_plan
        _db_url(),
        thread_id=thread_id,
    )


def _count_active(thread_id: UUID, status: str) -> int:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM research_plans"
            " WHERE thread_id = %s AND status = %s",
            (str(thread_id), status),
        )
        row = cur.fetchone()
        return int(row[0]) if row is not None else 0


_STEPS_A = [
    {"ordinal": 1, "description": "Pull latest"},
    {"ordinal": 2, "description": "Compare"},
]
_STEPS_B = [
    {"ordinal": 1, "description": "Pull latest"},
    {"ordinal": 2, "description": "Pull last year"},
    {"ordinal": 3, "description": "Compute delta"},
]


def test_propose_plan_first_call_creates_v1(thread_id: UUID, events: list) -> None:
    tokens = _bind(thread_id)
    try:
        result = propose_plan.invoke({"steps": _STEPS_A})
    finally:
        reset_memory_context(tokens)
    assert result["version"] == 1
    assert result["status"] == "proposed"
    assert _count_active(thread_id, "proposed") == 1


def test_propose_plan_second_call_supersedes_v1(thread_id: UUID, events: list) -> None:
    tokens = _bind(thread_id)
    try:
        propose_plan.invoke({"steps": _STEPS_A})
        second = propose_plan.invoke({"steps": _STEPS_B})
    finally:
        reset_memory_context(tokens)
    assert second["version"] == 2
    assert _count_active(thread_id, "proposed") == 1  # only v2 active
    assert _count_active(thread_id, "superseded") == 1  # v1 now superseded


def test_propose_plan_cap_returns_error(thread_id: UUID, events: list) -> None:
    tokens = _bind(thread_id)
    try:
        for _ in range(MAX_PLAN_VERSIONS):
            propose_plan.invoke({"steps": _STEPS_A})
        overflow = propose_plan.invoke({"steps": _STEPS_A})
    finally:
        reset_memory_context(tokens)
    assert overflow.get("error") == "MAX_PLAN_VERSIONS reached"
    assert overflow["version"] == MAX_PLAN_VERSIONS
    # No 6th row was inserted.
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM research_plans WHERE thread_id = %s",
            (str(thread_id),),
        )
        row = cur.fetchone()
        assert row is not None
        assert int(row[0]) == MAX_PLAN_VERSIONS
    # And the cap event fired.
    assert any(name == "research.plan.replan_capped" for name, _ in events)


def test_propose_plan_emits_drafted_event(thread_id: UUID, events: list) -> None:
    tokens = _bind(thread_id)
    try:
        result = propose_plan.invoke({"steps": _STEPS_A})
    finally:
        reset_memory_context(tokens)
    drafted = [(n, p) for n, p in events if n == "research.plan.drafted"]
    assert len(drafted) == 1
    name, payload = drafted[0]
    assert payload["plan_id"] == result["plan_id"]
    assert payload["version"] == 1
    assert payload["status"] == "proposed"
    assert payload["plan_json"]["steps"][0]["description"] == "Pull latest"


def test_propose_plan_errors_when_unbound() -> None:
    """No context bound → returns error dict, doesn't crash."""
    result = propose_plan.invoke({"steps": _STEPS_A})
    assert result == {"error": "agent_context_not_bound"}
