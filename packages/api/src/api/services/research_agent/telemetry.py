"""Structlog + counter conventions for the deep-research agent (HUG-207).

Every event the agent emits goes through `log_event(name, **fields)`,
which (a) writes a structlog line and (b) increments a self-counter
`hughes_research_telemetry_events_total{event_name=name}`. This
means production has a one-stop shop for "did event X fire?" — no
parsing logs to count occurrences.

Event names are constants so subsequent phases (planner, executor,
worker, verifier) can import them and we never accidentally drift
on the wire ("research.plan.drafted" vs "research.plan_drafted").

Trace context: `bind_research_context()` wraps
`structlog.contextvars.bind_contextvars` so any `log_event` (or
plain `slog.info`) within a turn carries `plan_id` / `plan_version`
/ `step_id` / `subagent_id`. Bindings clear with the contextvar
token when the turn exits — same pattern the chat agent uses for
`request_id`.

No business logic — pure plumbing. Consumers in subsequent issues
(L1, L2, L5, E1-E4, S1-S2, M1-M3, V1) import from here.
"""

from __future__ import annotations

from typing import Any

import structlog.contextvars

from api.logging import get_logger
from api.prometheus import research_telemetry_events_total

_slog = get_logger().bind(component="research")


# ---- event-name constants -----------------------------------------
# Naming: `research.<phase>.<verb>`. Keep alphabetically-ordered
# within each phase block so a diff highlights additions cleanly.

# Plan lifecycle.
EVENT_PLAN_DRAFTED = "research.plan.drafted"
EVENT_PLAN_DRAFT_FAILED = "research.plan.draft_failed"
EVENT_PLAN_APPROVED = "research.plan.approved"
EVENT_PLAN_ABORTED = "research.plan.aborted"
EVENT_PLAN_REVISED = "research.plan.revised"

# Step lifecycle.
EVENT_STEP_CREATED = "research.step.created"
EVENT_STEP_STARTED = "research.step.started"
EVENT_STEP_COMPLETED = "research.step.completed"
EVENT_STEP_FAILED = "research.step.failed"

# Findings + lead notes.
EVENT_FINDING_PERSISTED = "research.finding.persisted"
EVENT_LEAD_NOTE_WRITTEN = "research.lead.note_written"

# Subagent lifecycle (structlog-only; not surfaced via SSE).
EVENT_SUBAGENT_SPAWNED = "research.subagent.spawned"
EVENT_SUBAGENT_COMPLETED = "research.subagent.completed"
EVENT_SUBAGENT_FAILED = "research.subagent.failed"

# Turn-level.
EVENT_TURN_ROUTED = "research.turn.routed"
EVENT_TURN_COMPLETED = "research.turn.completed"

# Verifier (HUG-223 / V1).
EVENT_VERIFIER_INVOKED = "research.verifier.invoked"
EVENT_VERIFIER_FLAGGED = "research.verifier.flagged"


RESEARCH_EVENTS: frozenset[str] = frozenset(
    {
        EVENT_PLAN_DRAFTED,
        EVENT_PLAN_DRAFT_FAILED,
        EVENT_PLAN_APPROVED,
        EVENT_PLAN_ABORTED,
        EVENT_PLAN_REVISED,
        EVENT_STEP_CREATED,
        EVENT_STEP_STARTED,
        EVENT_STEP_COMPLETED,
        EVENT_STEP_FAILED,
        EVENT_FINDING_PERSISTED,
        EVENT_LEAD_NOTE_WRITTEN,
        EVENT_SUBAGENT_SPAWNED,
        EVENT_SUBAGENT_COMPLETED,
        EVENT_SUBAGENT_FAILED,
        EVENT_TURN_ROUTED,
        EVENT_TURN_COMPLETED,
        EVENT_VERIFIER_INVOKED,
        EVENT_VERIFIER_FLAGGED,
    }
)


# ---- API ----------------------------------------------------------


def bind_research_context(
    *,
    plan_id: str | None = None,
    plan_version: int | None = None,
    step_id: str | None = None,
    subagent_id: str | None = None,
) -> None:
    """Bind research-specific trace context for the current async
    task. Subsequent `log_event` / `slog.info` calls within the same
    task carry these fields automatically. Caller is responsible for
    unbinding via `structlog.contextvars.unbind_contextvars(...)` at
    turn teardown (mirrors the chat agent's `request_id` pattern)."""
    bindings: dict[str, Any] = {}
    if plan_id is not None:
        bindings["plan_id"] = plan_id
    if plan_version is not None:
        bindings["plan_version"] = plan_version
    if step_id is not None:
        bindings["step_id"] = step_id
    if subagent_id is not None:
        bindings["subagent_id"] = subagent_id
    if bindings:
        structlog.contextvars.bind_contextvars(**bindings)


def log_event(event_name: str, **fields: Any) -> None:
    """Emit a research event. Increments the self-counter
    `hughes_research_telemetry_events_total{event_name}` and writes
    a structlog line with the same name + `fields`.

    Unknown event names are accepted (no validation) but a warning
    is emitted so we notice typos. Validation in CI would catch
    them statically once the catalog stabilises."""
    if event_name not in RESEARCH_EVENTS:
        _slog.warning(
            "research.telemetry.unknown_event",
            attempted=event_name,
        )
    research_telemetry_events_total.labels(event_name=event_name).inc()
    _slog.info(event_name, **fields)
