"""Telemetry primitives — event constants, SSE builders, self-counter
(HUG-207).

Pure-Python tests; no DB or LLM dependencies. Mirrors the style of
the existing `test_agent_telemetry.py`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import structlog.contextvars
from api.prometheus import (
    research_telemetry_events_total,
    research_turns_total,
)
from api.services.research_agent import events, telemetry
from api.types.research import Finding, LeadNote, Plan, Step


def _make_plan() -> Plan:
    return Plan(
        plan_id=uuid4(),
        thread_id=uuid4(),
        version=1,
        status="draft",
        plan_json={"steps": [{"ordinal": 1, "description": "fetch"}]},
        created_at=datetime.now(UTC),
    )


def _make_step() -> Step:
    return Step(
        step_id=uuid4(),
        plan_id=uuid4(),
        ordinal=1,
        description="fetch loan balance by branch",
        status="running",
        assigned_subagent=None,
        started_at=datetime.now(UTC),
        completed_at=None,
    )


def _make_finding() -> Finding:
    return Finding(
        finding_id=uuid4(),
        step_id=uuid4(),
        summary_text="Main branch leads.",
        structured_rows_json=[{"branch": "Main", "balance": 1000.0}],
        mf_query_json={"metric": "deposit_balance"},
        cited_artifacts=None,
        created_at=datetime.now(UTC),
    )


def _make_note() -> LeadNote:
    return LeadNote(
        note_id=uuid4(),
        plan_id=uuid4(),
        version=1,
        body_md="# Lead's running notes\n\nKey decisions so far.",
        created_at=datetime.now(UTC),
    )


# ---- event-name constants ----------------------------------------


def test_all_event_names_start_with_research_dot() -> None:
    for name in telemetry.RESEARCH_EVENTS:
        assert name.startswith("research."), name


def test_event_constants_are_unique() -> None:
    """Catalog drift guard: if two constants ever collide on the
    same string, structlog will conflate them and Prometheus will
    over-count. Fail loud at import time."""
    assert len(telemetry.RESEARCH_EVENTS) == 18


def test_constants_match_canonical_strings() -> None:
    """Spot-check the constants individually so a renamed event in
    one place but not the other gets caught."""
    assert telemetry.EVENT_PLAN_DRAFTED == "research.plan.drafted"
    assert telemetry.EVENT_STEP_COMPLETED == "research.step.completed"
    assert telemetry.EVENT_SUBAGENT_SPAWNED == "research.subagent.spawned"


# ---- SSE builders ------------------------------------------------


def test_plan_drafted_event_shape() -> None:
    plan = _make_plan()
    out = events.plan_drafted_event(plan)
    assert out["event"] == "research.plan.drafted"
    payload = json.loads(out["data"])
    assert payload["plan_id"] == str(plan.plan_id)
    assert payload["version"] == 1
    assert payload["plan_json"] == plan.plan_json


def test_plan_revised_event_carries_prior_version() -> None:
    plan = _make_plan()
    plan = plan.model_copy(update={"version": 2, "status": "approved"})
    out = events.plan_revised_event(plan, prior_version=1)
    assert out["event"] == "research.plan.revised"
    payload = json.loads(out["data"])
    assert payload["version"] == 2
    assert payload["prior_version"] == 1


def test_step_started_event_shape() -> None:
    step = _make_step()
    out = events.step_started_event(step)
    assert out["event"] == "research.step.started"
    payload = json.loads(out["data"])
    assert payload["step_id"] == str(step.step_id)
    assert payload["ordinal"] == 1
    assert "fetch loan balance" in payload["description"]


def test_step_failed_event_truncates_long_error() -> None:
    step = _make_step()
    long = "x" * 1000
    out = events.step_failed_event(step, error=long)
    payload = json.loads(out["data"])
    assert len(payload["error"]) == 500


def test_finding_persisted_event_counts_rows() -> None:
    finding = _make_finding()
    out = events.finding_persisted_event(finding)
    payload = json.loads(out["data"])
    assert payload["row_count"] == 1


def test_finding_event_handles_null_rows() -> None:
    finding = _make_finding().model_copy(update={"structured_rows_json": None})
    out = events.finding_persisted_event(finding)
    payload = json.loads(out["data"])
    assert payload["row_count"] == 0


def test_lead_note_event_truncates_long_body() -> None:
    note = _make_note().model_copy(update={"body_md": "x" * 1000})
    out = events.lead_note_event(note)
    payload = json.loads(out["data"])
    assert len(payload["preview"]) <= 280
    assert payload["body_chars"] == 1000


def test_lead_note_event_preserves_short_body() -> None:
    note = _make_note()
    out = events.lead_note_event(note)
    payload = json.loads(out["data"])
    assert payload["preview"] == note.body_md


# ---- log_event self-counter --------------------------------------


def test_log_event_increments_self_counter() -> None:
    before = research_telemetry_events_total.labels(
        event_name=telemetry.EVENT_TURN_COMPLETED
    )._value.get()  # type: ignore[attr-defined]
    telemetry.log_event(telemetry.EVENT_TURN_COMPLETED, elapsed_ms=42)
    after = research_telemetry_events_total.labels(
        event_name=telemetry.EVENT_TURN_COMPLETED
    )._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_log_event_warns_on_unknown_event() -> None:
    """Unknown event names still emit (no exception) — they just log a
    warning so we notice typos. We don't assert the warning content
    here; the structlog log capture would need extra wiring."""
    telemetry.log_event("research.plan.invented", extra="foo")  # no raise


# ---- bind_research_context ---------------------------------------


def test_bind_research_context_adds_fields_to_contextvars() -> None:
    structlog.contextvars.clear_contextvars()
    telemetry.bind_research_context(
        plan_id="p-123", plan_version=2, step_id="s-456"
    )
    bound = structlog.contextvars.get_contextvars()
    assert bound["plan_id"] == "p-123"
    assert bound["plan_version"] == 2
    assert bound["step_id"] == "s-456"
    assert "subagent_id" not in bound  # None args are not bound
    structlog.contextvars.clear_contextvars()


def test_bind_research_context_no_args_is_noop() -> None:
    structlog.contextvars.clear_contextvars()
    telemetry.bind_research_context()
    assert not structlog.contextvars.get_contextvars()


# ---- Prometheus wiring -------------------------------------------


def test_research_turns_counter_supports_route_label() -> None:
    """Sanity check that the labelled counter accepts our route
    values without raising."""
    research_turns_total.labels(route="shallow").inc()
    research_turns_total.labels(route="deep").inc()
