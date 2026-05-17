"""run_subagent tool tests (HUG-243 + Issue 1 batch refactor, 2026-05-17).

run_subagent now accepts a LIST of sub-questions and fans out workers
in parallel. These tests stub the worker graph (no real LLM) and
exercise the batch persistence + event emission + result aggregation.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import UUID

import psycopg
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from nl_engine.agent.memory_context import (
    bind_memory_context,
    reset_memory_context,
)
from nl_engine.agent.run_context import (
    bind_event_emitter,
    reset_event_emitter,
)
from nl_engine.agent.subagent_tool import (
    MAX_SUBAGENTS_PER_BATCH,
    run_subagent,
)
from nl_engine.repo import subagent_calls

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    url = _db_url()
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id, title)"
            " VALUES (gen_random_uuid(), 'subtest', 'subtest', 'sub')"
            " RETURNING thread_id"
        )
        row = cur.fetchone()
        assert row is not None
        tid = UUID(str(row[0]))
    try:
        yield tid
    finally:
        with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM threads WHERE session_id = 'subtest'")


@pytest.fixture
def events() -> Iterator[list[tuple[str, dict]]]:
    recorded: list[tuple[str, dict]] = []

    def emit(name: str, payload: dict) -> None:
        recorded.append((name, payload))

    token = bind_event_emitter(emit)
    try:
        yield recorded
    finally:
        reset_event_emitter(token)


def _bind(thread_id: UUID):
    return bind_memory_context(UUID(int=0), _db_url(), thread_id=thread_id)


# ── Stub worker graph ────────────────────────────────────────────────


class _StubGraph:
    """Stand-in for a compiled LangGraph instance. Each `invoke` call
    returns whatever `.result` is set to. For batch tests we accept a
    callable that produces results per-invocation so parallel dispatch
    can return different payloads."""

    def __init__(self, result_or_fn) -> None:
        self._r = result_or_fn

    def invoke(self, state):
        if callable(self._r):
            return self._r(state)
        return self._r


def _patch_worker_graph(monkeypatch, graph_or_factory) -> None:
    from nl_engine.agent import subagent_tool

    if callable(graph_or_factory) and not isinstance(graph_or_factory, _StubGraph):
        monkeypatch.setattr(subagent_tool, "_build_worker_graph", graph_or_factory)
    else:
        monkeypatch.setattr(
            subagent_tool, "_build_worker_graph", lambda: graph_or_factory
        )


def _final_answer_tool_message(summary: str, rows=None, mf_query=None) -> ToolMessage:
    import json

    payload = {"summary": summary, "rows": rows, "mf_query": mf_query}
    return ToolMessage(
        content=json.dumps(payload), name="final_answer", tool_call_id="stub-call-1"
    )


def _final_messages(summary: str, rows=None, mf_query=None):
    return {
        "messages": [
            HumanMessage(content="q"),
            _final_answer_tool_message(summary, rows, mf_query),
        ]
    }


# ── Tests ────────────────────────────────────────────────────────────


def test_run_subagent_batch_persists_one_row_per_entry(
    monkeypatch, thread_id, events
) -> None:
    graph = _StubGraph(_final_messages("done"))
    _patch_worker_graph(monkeypatch, graph)
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke(
            {
                "subagents": [
                    {"prompt": "q1", "plan_step_ordinal": 1},
                    {"prompt": "q2", "plan_step_ordinal": 2},
                    {"prompt": "q3", "plan_step_ordinal": 3},
                ]
            }
        )
    finally:
        reset_memory_context(tokens)
    assert isinstance(result, list)
    assert len(result) == 3
    for entry in result:
        assert "call_id" in entry
        row = subagent_calls.get_call(UUID(entry["call_id"]), _db_url())
        assert row is not None
        assert row["thread_id"] == thread_id
        assert row["status"] == "complete"


def test_run_subagent_returns_each_workers_final_answer(
    monkeypatch, thread_id, events
) -> None:
    # Different payload per invocation so we can verify per-entry results.
    payloads = iter(
        [
            _final_messages("A", rows=[{"k": "a"}], mf_query={"metric": "m_a"}),
            _final_messages("B", rows=[{"k": "b"}], mf_query={"metric": "m_b"}),
        ]
    )
    _patch_worker_graph(
        monkeypatch, lambda: _StubGraph(lambda _s: next(payloads))
    )
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke(
            {"subagents": [{"prompt": "qA"}, {"prompt": "qB"}]}
        )
    finally:
        reset_memory_context(tokens)
    summaries = {r["summary"] for r in result}
    assert summaries == {"A", "B"}


def test_run_subagent_emits_spawned_and_completed_for_each(
    monkeypatch, thread_id, events
) -> None:
    _patch_worker_graph(monkeypatch, _StubGraph(_final_messages("ok")))
    tokens = _bind(thread_id)
    try:
        run_subagent.invoke({"subagents": [{"prompt": "a"}, {"prompt": "b"}]})
    finally:
        reset_memory_context(tokens)
    spawned = [n for n, _ in events if n == "research.subagent.spawned"]
    completed = [n for n, _ in events if n == "research.subagent.completed"]
    assert len(spawned) == 2
    assert len(completed) == 2


def test_run_subagent_partial_failure_does_not_abort_batch(
    monkeypatch, thread_id, events
) -> None:
    # First worker succeeds; second raises; third hits no-final-answer.
    payloads: list = [
        _final_messages("ok"),
        RuntimeError("boom"),
        {"messages": [AIMessage(content="...")]},  # no ToolMessage → fail
    ]
    it = iter(payloads)

    def _invoke(_state):
        val = next(it)
        if isinstance(val, Exception):
            raise val
        return val

    _patch_worker_graph(monkeypatch, lambda: _StubGraph(_invoke))
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke(
            {
                "subagents": [
                    {"prompt": "ok"},
                    {"prompt": "explode"},
                    {"prompt": "stuck"},
                ]
            }
        )
    finally:
        reset_memory_context(tokens)
    assert len(result) == 3
    statuses = []
    for entry in result:
        row = subagent_calls.get_call(UUID(entry["call_id"]), _db_url())
        assert row is not None
        statuses.append(row["status"])
    assert statuses.count("complete") == 1
    assert statuses.count("failed") == 2
    failed_events = [n for n, _ in events if n == "research.subagent.failed"]
    assert len(failed_events) == 2


def test_run_subagent_empty_list_returns_empty(thread_id) -> None:
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke({"subagents": []})
    finally:
        reset_memory_context(tokens)
    assert result == []


def test_run_subagent_over_cap_returns_error(thread_id) -> None:
    tokens = _bind(thread_id)
    try:
        too_many = [{"prompt": f"q{i}"} for i in range(MAX_SUBAGENTS_PER_BATCH + 1)]
        result = run_subagent.invoke({"subagents": too_many})
    finally:
        reset_memory_context(tokens)
    assert isinstance(result, list)
    assert len(result) == 1
    assert "error" in result[0]
    assert "too many" in result[0]["error"].lower()


def test_run_subagent_cannot_recurse() -> None:
    """The subagent's _build_worker_graph constructs from ALL_TOOLS,
    which does NOT include run_subagent / propose_plan / memory tools."""
    from nl_engine.agent.tools import ALL_TOOLS

    names = {t.name for t in ALL_TOOLS}
    assert "run_subagent" not in names
    assert "propose_plan" not in names
    assert "read_memory" not in names
    assert "write_memory" not in names


def test_run_subagent_errors_when_unbound() -> None:
    """No context bound → returns single-entry error list."""
    result = run_subagent.invoke({"subagents": [{"prompt": "no-context"}]})
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == {"error": "agent_context_not_bound"}
