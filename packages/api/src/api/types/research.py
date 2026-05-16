"""Pydantic models for the deep-research persistence layer (HUG-203).

Backs the four tables introduced in migration 016: `research_plans`,
`research_steps`, `research_findings`, `research_lead_notes`. The
status enums mirror the CHECK constraints in the migration — keep
them in sync.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

PlanStatus = Literal[
    "draft",
    "approved",
    "running",
    "complete",
    "aborted",
    "failed",
    "superseded",
    # HUG-241 / migration 017: the autonomous lead-agent's `propose_plan`
    # tool writes rows with this status. Listed last to avoid disturbing
    # the existing ordering used by status-comparing tests.
    "proposed",
]

StepStatus = Literal[
    "pending",
    "running",
    "complete",
    "failed",
    "skipped",
]


class Plan(BaseModel):
    plan_id: UUID
    thread_id: UUID
    version: int
    status: PlanStatus
    plan_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class Step(BaseModel):
    step_id: UUID
    plan_id: UUID
    ordinal: int
    description: str
    status: StepStatus
    assigned_subagent: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Finding(BaseModel):
    finding_id: UUID
    step_id: UUID
    summary_text: str | None = None
    # Subagent's structured output. List of row-dicts when the worker
    # produced tabular data (e.g. mf_query result rows); None otherwise.
    structured_rows_json: list[dict[str, Any]] | None = None
    # The `mf_query` tool args the worker used to produce these rows.
    mf_query_json: dict[str, Any] | None = None
    # Free-form citations: metric IDs, time windows, source rows.
    # List-of-dicts is just convention; we don't typecheck the shape
    # because callers vary.
    cited_artifacts: list[dict[str, Any]] | None = None
    created_at: datetime


class LeadNote(BaseModel):
    """One version of the lead's running markdown — the 'external plan
    memory' primitive from Anthropic's lead+subagents pattern. The
    lead reads the latest note on every tick to stay coherent across
    context truncations."""

    note_id: UUID
    plan_id: UUID
    version: int
    body_md: str
    created_at: datetime
