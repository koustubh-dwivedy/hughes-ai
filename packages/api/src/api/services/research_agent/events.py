"""SSE event builders for the deep-research feature (HUG-207).

Pure functions over the typed models in `api.types.research`. Each
returns a `{"event": "...", "data": json_dumps(...)}` dict — the
shape `sse_starlette.EventSourceResponse` consumes.

This module is intentionally side-effect-free (no structlog, no
counters) so unit tests can assert shape without standing up the
telemetry stack. Callers (coordinator / planner / executor /
workers) call BOTH `events.X(...)` (to yield via SSE) AND
`telemetry.log_event(...)` (to record the event). Two-call pattern
keeps each module a clean concern.
"""

from __future__ import annotations

import json
from typing import Any

from api.services.research_agent.telemetry import (
    EVENT_FINDING_PERSISTED,
    EVENT_LEAD_NOTE_WRITTEN,
    EVENT_PLAN_ABORTED,
    EVENT_PLAN_APPROVED,
    EVENT_PLAN_DRAFTED,
    EVENT_PLAN_REVISED,
    EVENT_STEP_COMPLETED,
    EVENT_STEP_FAILED,
    EVENT_STEP_STARTED,
)
from api.types.research import Finding, LeadNote, Plan, Step

# ---- helpers ------------------------------------------------------


def _event(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Common shape: {"event": name, "data": json.dumps(payload)}.
    JSON serialization here so callers don't worry about default=str
    quirks per call site."""
    return {"event": name, "data": json.dumps(payload, default=str)}


# ---- plan events --------------------------------------------------


def plan_drafted_event(plan: Plan) -> dict[str, Any]:
    return _event(
        EVENT_PLAN_DRAFTED,
        {
            "plan_id": str(plan.plan_id),
            "thread_id": str(plan.thread_id),
            "version": plan.version,
            "status": plan.status,
            "plan_json": plan.plan_json,
        },
    )


def plan_approved_event(plan: Plan) -> dict[str, Any]:
    return _event(
        EVENT_PLAN_APPROVED,
        {
            "plan_id": str(plan.plan_id),
            "version": plan.version,
        },
    )


def plan_aborted_event(plan: Plan) -> dict[str, Any]:
    return _event(
        EVENT_PLAN_ABORTED,
        {
            "plan_id": str(plan.plan_id),
            "version": plan.version,
        },
    )


def plan_revised_event(plan: Plan, *, prior_version: int) -> dict[str, Any]:
    """Emitted when the lead writes a new plan version mid-turn
    (M2). `prior_version` is the version that got superseded so the
    UI can render a 'View previous plan (vN)' affordance without a
    follow-up fetch."""
    return _event(
        EVENT_PLAN_REVISED,
        {
            "plan_id": str(plan.plan_id),
            "thread_id": str(plan.thread_id),
            "version": plan.version,
            "prior_version": prior_version,
            "plan_json": plan.plan_json,
        },
    )


# ---- step events --------------------------------------------------


def step_started_event(step: Step) -> dict[str, Any]:
    return _event(
        EVENT_STEP_STARTED,
        {
            "step_id": str(step.step_id),
            "plan_id": str(step.plan_id),
            "ordinal": step.ordinal,
            "description": step.description,
            "assigned_subagent": step.assigned_subagent,
        },
    )


def step_completed_event(step: Step) -> dict[str, Any]:
    return _event(
        EVENT_STEP_COMPLETED,
        {
            "step_id": str(step.step_id),
            "ordinal": step.ordinal,
            "completed_at": step.completed_at,
        },
    )


def step_failed_event(step: Step, *, error: str) -> dict[str, Any]:
    return _event(
        EVENT_STEP_FAILED,
        {
            "step_id": str(step.step_id),
            "ordinal": step.ordinal,
            "error": error[:500],
        },
    )


# ---- finding / lead-note events -----------------------------------


def finding_persisted_event(finding: Finding) -> dict[str, Any]:
    """Surfaced to the UI so the workspace can render the finding card
    as soon as the worker writes it (before the lead synthesises)."""
    return _event(
        EVENT_FINDING_PERSISTED,
        {
            "finding_id": str(finding.finding_id),
            "step_id": str(finding.step_id),
            "summary_text": finding.summary_text,
            "row_count": (
                len(finding.structured_rows_json)
                if finding.structured_rows_json is not None
                else 0
            ),
        },
    )


def lead_note_event(note: LeadNote) -> dict[str, Any]:
    """The lead's running notes are part of the audit trail. We emit
    only the metadata + a short preview over SSE so the UI shows
    'lead is thinking…' style copy without re-streaming full bodies."""
    preview = note.body_md if len(note.body_md) <= 280 else (
        note.body_md[:277] + "…"
    )
    return _event(
        EVENT_LEAD_NOTE_WRITTEN,
        {
            "note_id": str(note.note_id),
            "plan_id": str(note.plan_id),
            "version": note.version,
            "preview": preview,
            "body_chars": len(note.body_md),
        },
    )
