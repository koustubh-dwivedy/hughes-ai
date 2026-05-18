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
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from nl_engine.agent import subagent_tool
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
    _invoke_worker,
    run_subagent,
)
from nl_engine.agent.tools import ALL_TOOLS, LEAD_AGENT_TOOLS
from nl_engine.agent.worker_agent_prompt import WORKER_AGENT_SYSTEM_PROMPT
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
    result = run_subagent.invoke({"subagents": [{"prompt": "x"}]})
    assert result == [{"error": "agent_context_not_bound"}]


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


# ── HUG-260: worker-specific system prompt ──────────────────────────


def test_worker_prompt_includes_anchor_w_rules() -> None:
    """The 4 worker rules (empty=valid, multi-step OK, always final_answer,
    step-budget awareness) must be present in the worker prompt — they
    are the load-bearing fix for the 2026-05-18 step-cap bug."""
    p = WORKER_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-W" in p
    assert "Empty / null / zero results are valid answers" in p
    assert "Multi-step work is allowed" in p
    assert "Every worker run terminates in `final_answer`" in p
    assert "Step-budget awareness" in p
    assert "10 LLM turns" in p


def test_worker_prompt_includes_data_query_rules() -> None:
    """Workers still need the ANCHOR-A..E rules + MetricFlow tool-calling
    rules; only the OpenUI rendering / DSL sections are stripped."""
    p = WORKER_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-A" in p  # latest-month filter
    assert "ANCHOR-B" in p  # by-X grouping
    assert "MetricFlow tool-calling rules" in p


def test_worker_prompt_excludes_openui_sections() -> None:
    """Workers must NOT emit OpenUI DSL — chart synthesis is the lead's
    job. Stripping the OpenUI sections also keeps the worker prompt
    small enough that the 10-step budget isn't eaten by long-context
    LLM latency."""
    p = WORKER_AGENT_SYSTEM_PROMPT
    assert "## OpenUI rendering" not in p
    assert "OpenUI Lang reference" not in p
    assert "openui_dsl" in p  # one mention is fine — the W rules tell
    # the worker NOT to populate it. The OpenUI grammar itself is absent.
    assert "=== OpenUI Lang reference" not in p


def test_invoke_worker_prepends_worker_system_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_invoke_worker` must put a SystemMessage with the worker prompt
    at messages[0]. `ensure_system_prompt` no-ops when messages[0] is
    already a SystemMessage, so this is how we override the chat
    agent's default prompt without touching shared code."""
    captured: dict[str, list] = {}

    class _FakeGraph:
        def invoke(self, state: object) -> dict:
            captured["messages"] = list(getattr(state, "messages", []))
            return {"messages": []}

    monkeypatch.setattr(
        subagent_tool, "_build_worker_graph", lambda: _FakeGraph()
    )
    _invoke_worker("test prompt", request_id=str(uuid4()))

    msgs = captured["messages"]
    assert len(msgs) == 2
    assert isinstance(msgs[0], SystemMessage)
    assert msgs[0].content == WORKER_AGENT_SYSTEM_PROMPT
    assert isinstance(msgs[1], HumanMessage)
    assert msgs[1].content == "test prompt"
