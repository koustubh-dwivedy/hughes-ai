"""Unit tests for the lead-agent surface that don't need a live DB
(HUG-241 / HUG-242 / HUG-243).

The integration-style tests in test_lead_memory / test_propose_plan /
test_run_subagent are `pytest.mark.db` and only run in the integration
job; this file exercises the pure-Python paths so the Unit Tests job's
coverage gate stays above floor.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from nl_engine.agent.memory_context import (
    MemoryContextNotBoundError,
    bind_memory_context,
    current_db_url,
    current_plan_id,
    current_thread_id,
    reset_memory_context,
)
from nl_engine.agent.memory_tools import read_memory, write_memory
from nl_engine.agent.plan_tool import PlanStepDescriptor, propose_plan
from nl_engine.agent.run_context import (
    bind_event_emitter,
    emit_run_event,
    reset_event_emitter,
)
from nl_engine.agent.subagent_tool import (
    WORKER_MAX_STEPS,
    _extract_final_answer,
    run_subagent,
)
from nl_engine.agent.tools import ALL_TOOLS, LEAD_AGENT_TOOLS
from nl_engine.repo.lead_memory import MAX_NOTE_CHARS
from nl_engine.repo.plans import MAX_PLAN_VERSIONS

# ── Memory context ──────────────────────────────────────────────────


def test_memory_context_unbound_raises() -> None:
    with pytest.raises(MemoryContextNotBoundError):
        current_plan_id()
    with pytest.raises(MemoryContextNotBoundError):
        current_db_url()
    with pytest.raises(MemoryContextNotBoundError):
        current_thread_id()


def test_memory_context_bind_and_reset() -> None:
    pid = uuid4()
    tid = uuid4()
    tokens = bind_memory_context(pid, "postgres://x", thread_id=tid)
    try:
        assert current_plan_id() == pid
        assert current_db_url() == "postgres://x"
        assert current_thread_id() == tid
    finally:
        reset_memory_context(tokens)
    # After reset, defaults restored:
    with pytest.raises(MemoryContextNotBoundError):
        current_plan_id()


# ── Run context (event emitter) ─────────────────────────────────────


def test_emit_run_event_noop_when_unbound() -> None:
    emit_run_event("any.event", {"k": "v"})  # must not raise


def test_emit_run_event_invokes_bound_callback() -> None:
    seen: list[tuple[str, dict]] = []

    def cb(name: str, payload: dict) -> None:
        seen.append((name, payload))

    token = bind_event_emitter(cb)
    try:
        emit_run_event("a", {"x": 1})
        emit_run_event("b", {"y": 2})
    finally:
        reset_event_emitter(token)
    assert seen == [("a", {"x": 1}), ("b", {"y": 2})]
    # After reset, becomes a no-op again.
    emit_run_event("never_seen", {})
    assert len(seen) == 2


# ── Memory tools (unbound) ──────────────────────────────────────────


def test_read_memory_unbound_returns_error_dict() -> None:
    result = read_memory.invoke({"key": "x"})
    assert result == {"body": None, "error": "memory_context_not_bound"}


def test_write_memory_unbound_returns_error_dict() -> None:
    result = write_memory.invoke({"key": "x", "body": "y"})
    assert result == {"error": "memory_context_not_bound"}


# ── Plan tool ───────────────────────────────────────────────────────


def test_propose_plan_unbound_returns_error_dict() -> None:
    result = propose_plan.invoke({"steps": [{"ordinal": 1, "description": "x"}]})
    assert result == {"error": "agent_context_not_bound"}


def test_plan_step_descriptor_schema() -> None:
    s = PlanStepDescriptor(ordinal=2, description="do thing", notes="why")
    assert s.ordinal == 2
    assert s.description == "do thing"
    assert s.notes == "why"
    s2 = PlanStepDescriptor(ordinal=1, description="only desc")
    assert s2.notes is None


# ── Subagent tool ───────────────────────────────────────────────────


def test_run_subagent_unbound_returns_error_dict() -> None:
    result = run_subagent.invoke({"prompt": "x"})
    assert result == {"error": "agent_context_not_bound"}


def test_extract_final_answer_parses_json_content() -> None:
    msg = ToolMessage(
        content='{"summary": "ok", "rows": [{"a": 1}]}',
        name="final_answer",
        tool_call_id="t1",
    )
    parsed = _extract_final_answer([HumanMessage(content="q"), msg])
    assert parsed == {"summary": "ok", "rows": [{"a": 1}]}


def test_extract_final_answer_returns_none_for_unrelated_tool() -> None:
    msg = ToolMessage(content="{}", name="list_metrics", tool_call_id="t1")
    assert _extract_final_answer([msg]) is None


def test_extract_final_answer_returns_none_when_absent() -> None:
    assert _extract_final_answer([AIMessage(content="...")]) is None


def test_extract_final_answer_handles_malformed_json() -> None:
    msg = ToolMessage(content="not valid json", name="final_answer", tool_call_id="t1")
    result = _extract_final_answer([msg])
    assert result == {"summary": "not valid json"}


def test_extract_final_answer_returns_none_for_json_non_dict() -> None:
    msg = ToolMessage(content='"just a string"', name="final_answer", tool_call_id="t1")
    assert _extract_final_answer([msg]) is None


def test_worker_max_steps_is_ten() -> None:
    assert WORKER_MAX_STEPS == 10


# ── Tool registries ─────────────────────────────────────────────────


def test_all_tools_excludes_lead_only_tools() -> None:
    names = {t.name for t in ALL_TOOLS}
    assert "run_subagent" not in names
    assert "propose_plan" not in names
    assert "read_memory" not in names
    assert "write_memory" not in names


def test_lead_agent_tools_includes_extras() -> None:
    names = {t.name for t in LEAD_AGENT_TOOLS}
    assert {"run_subagent", "propose_plan", "read_memory", "write_memory"} <= names


def test_lead_agent_tools_excludes_direct_data_fetches() -> None:
    """The lead orchestrates; workers fetch. Direct data tools must be
    absent so the model cannot bypass delegation."""
    names = {t.name for t in LEAD_AGENT_TOOLS}
    assert "mf_query" not in names, (
        "lead must delegate data reads via run_subagent — mf_query is a "
        "worker-only tool"
    )
    assert "lookup_metric_definition" not in names, (
        "lead must delegate data reads — lookup_metric_definition is "
        "worker-only"
    )


def test_lead_agent_tools_keeps_list_metrics() -> None:
    """list_metrics is read-only catalog discovery; the lead needs it
    to write good sub-questions for workers."""
    names = {t.name for t in LEAD_AGENT_TOOLS}
    assert "list_metrics" in names


def test_lead_agent_tools_complete_allow_list() -> None:
    """Exact allow-list so adding a new lead tool requires updating the
    test deliberately."""
    names = {t.name for t in LEAD_AGENT_TOOLS}
    expected = {
        "list_metrics",
        "clarify",
        "final_answer",
        "read_memory",
        "write_memory",
        "propose_plan",
        "run_subagent",
    }
    assert names == expected, f"unexpected diff: {names ^ expected}"


# ── Constants ───────────────────────────────────────────────────────


def test_max_note_chars_is_2000() -> None:
    assert MAX_NOTE_CHARS == 2000


def test_max_plan_versions_is_5() -> None:
    assert MAX_PLAN_VERSIONS == 5
