"""run_subagent tool tests (HUG-243).

Worker graph compilation is monkey-patched so we don't actually invoke
an LLM — we stub it to return a pre-canned final_answer ToolMessage,
or to fail in specific ways. Persistence + event emission are observed
through DB rows + the run_context emitter.
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
from nl_engine.agent.subagent_tool import run_subagent
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
    """Stand-in for a compiled LangGraph instance.

    `invoke(state)` returns whatever `.next_result` is set to. Tests can
    swap behaviour per case."""

    def __init__(self, result: dict) -> None:
        self.result = result
        self.captured_state = None

    def invoke(self, state):
        self.captured_state = state
        return self.result


def _patch_worker_graph(monkeypatch, graph: _StubGraph) -> None:
    """Patch `_build_worker_graph` to return the stub."""
    from nl_engine.agent import subagent_tool

    monkeypatch.setattr(
        subagent_tool, "_build_worker_graph", lambda: graph
    )


def _final_answer_tool_message(summary: str, rows=None, mf_query=None) -> ToolMessage:
    import json

    payload = {"summary": summary, "rows": rows, "mf_query": mf_query}
    return ToolMessage(
        content=json.dumps(payload),
        name="final_answer",
        tool_call_id="stub-call-1",
    )


# ── Tests ────────────────────────────────────────────────────────────


def test_run_subagent_persists_call_row(monkeypatch, thread_id, events) -> None:
    graph = _StubGraph(
        {"messages": [HumanMessage(content="q"), _final_answer_tool_message("done")]}
    )
    _patch_worker_graph(monkeypatch, graph)
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke({"prompt": "sub-question", "plan_step_ordinal": 2})
    finally:
        reset_memory_context(tokens)
    assert "call_id" in result
    row = subagent_calls.get_call(UUID(result["call_id"]), _db_url())
    assert row is not None
    assert row["thread_id"] == thread_id
    assert row["prompt"] == "sub-question"
    assert row["plan_step_ordinal"] == 2
    assert row["status"] == "complete"


def test_run_subagent_returns_final_answer_payload(
    monkeypatch, thread_id, events
) -> None:
    graph = _StubGraph(
        {
            "messages": [
                HumanMessage(content="q"),
                _final_answer_tool_message(
                    "the answer",
                    rows=[{"a": 1}],
                    mf_query={"metric": "x"},
                ),
            ]
        }
    )
    _patch_worker_graph(monkeypatch, graph)
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke({"prompt": "go"})
    finally:
        reset_memory_context(tokens)
    assert result["summary"] == "the answer"
    assert result["rows"] == [{"a": 1}]
    assert result["mf_query"] == {"metric": "x"}


def test_run_subagent_cannot_recurse() -> None:
    """The subagent's _build_worker_graph constructs from ALL_TOOLS,
    which does NOT include run_subagent / propose_plan / memory tools.
    Verify this at the import level so we don't ship a regression."""
    from nl_engine.agent.tools import ALL_TOOLS

    names = {t.name for t in ALL_TOOLS}
    assert "run_subagent" not in names
    assert "propose_plan" not in names
    assert "read_memory" not in names
    assert "write_memory" not in names


def test_run_subagent_no_final_answer_persists_failure(
    monkeypatch, thread_id, events
) -> None:
    """Worker hits step cap or otherwise never emits final_answer →
    row is marked failed, failed event emits."""
    graph = _StubGraph({"messages": [AIMessage(content="...")]})  # no ToolMessage
    _patch_worker_graph(monkeypatch, graph)
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke({"prompt": "stuck"})
    finally:
        reset_memory_context(tokens)
    assert "error" in result
    row = subagent_calls.get_call(UUID(result["call_id"]), _db_url())
    assert row is not None
    assert row["status"] == "failed"
    assert "final_answer" in (row["error_text"] or "")
    assert any(name == "research.subagent.failed" for name, _ in events)


def test_run_subagent_exception_persists_failure(
    monkeypatch, thread_id, events
) -> None:
    """Worker invocation raises → row failed, error captured, failed event fires."""

    class _ExplodingGraph:
        def invoke(self, _state):
            raise RuntimeError("boom")

    _patch_worker_graph(monkeypatch, _ExplodingGraph())  # type: ignore[arg-type]
    tokens = _bind(thread_id)
    try:
        result = run_subagent.invoke({"prompt": "x"})
    finally:
        reset_memory_context(tokens)
    assert "error" in result
    row = subagent_calls.get_call(UUID(result["call_id"]), _db_url())
    assert row is not None
    assert row["status"] == "failed"
    assert "boom" in (row["error_text"] or "")
    assert any(name == "research.subagent.failed" for name, _ in events)


def test_run_subagent_emits_spawned_and_completed_events(
    monkeypatch, thread_id, events
) -> None:
    graph = _StubGraph(
        {"messages": [_final_answer_tool_message("ok")]}
    )
    _patch_worker_graph(monkeypatch, graph)
    tokens = _bind(thread_id)
    try:
        run_subagent.invoke({"prompt": "p"})
    finally:
        reset_memory_context(tokens)
    names = [n for n, _ in events]
    assert "research.subagent.spawned" in names
    assert "research.subagent.completed" in names


def test_run_subagent_errors_when_unbound() -> None:
    """No context bound → returns error dict, doesn't crash."""
    result = run_subagent.invoke({"prompt": "no-context"})
    assert result == {"error": "agent_context_not_bound"}
