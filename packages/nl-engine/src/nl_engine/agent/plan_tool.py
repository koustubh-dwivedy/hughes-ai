"""Lead-agent `propose_plan` tool (HUG-242).

Persists a research plan version for transparency/audit. No interrupt —
the lead continues immediately after the tool returns. May be called
multiple times per turn to revise; old versions are flipped to
`superseded`. Hard cap of `MAX_PLAN_VERSIONS=5` versions per thread.

The frontend renders the latest version informationally via the
`research.plan.drafted` SSE event emitted alongside the persistence
(emitter is bound by the agent runner via `bind_event_emitter`; if no
emitter is bound, the tool persists silently — the DB is still the
source of truth).
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from nl_engine.agent.memory_context import (
    MemoryContextNotBoundError,
    current_db_url,
    current_thread_id,
)
from nl_engine.agent.run_context import emit_run_event
from nl_engine.logging import get_logger
from nl_engine.repo.plans import (
    MAX_PLAN_VERSIONS,
    propose_or_supersede_plan,
)

slog = get_logger().bind(component="agent.plan_tool")


class PlanStepDescriptor(BaseModel):
    """One step in a proposed plan. The lead emits a sequence of these
    when it calls propose_plan; the frontend renders the list and the
    runner persists them in `research_plans.plan_json`."""

    ordinal: int = Field(description="1-based position of this step in the plan.")
    description: str = Field(
        description=(
            "What this step accomplishes — a short, action-oriented "
            "sentence the user can scan in the PlanPreview UI."
        )
    )
    notes: str | None = Field(
        default=None,
        description=(
            "Optional clarifying note for this step (assumptions, "
            "dependencies, expected output shape). Keep short."
        ),
    )


def _capped_response(
    thread_id: Any, result: Any
) -> dict[str, Any]:
    slog.warning(
        "agent.propose_plan.capped",
        thread_id=str(thread_id),
        version=result.version,
        cap=MAX_PLAN_VERSIONS,
    )
    emit_run_event(
        "research.plan.replan_capped",
        {
            "plan_id": str(result.plan_id),
            "version": result.version,
            "cap": MAX_PLAN_VERSIONS,
        },
    )
    return {
        "error": "MAX_PLAN_VERSIONS reached",
        "plan_id": str(result.plan_id),
        "version": result.version,
        "cap": MAX_PLAN_VERSIONS,
    }


def _drafted_response(
    thread_id: Any, result: Any, plan_json: dict[str, Any], step_count: int
) -> dict[str, Any]:
    slog.info(
        "agent.propose_plan",
        thread_id=str(thread_id),
        plan_id=str(result.plan_id),
        version=result.version,
        step_count=step_count,
    )
    emit_run_event(
        "research.plan.drafted",
        {
            "plan_id": str(result.plan_id),
            "thread_id": str(thread_id),
            "version": result.version,
            "status": "proposed",
            "plan_json": plan_json,
        },
    )
    return {
        "plan_id": str(result.plan_id),
        "version": result.version,
        "status": "proposed",
    }


@tool
def propose_plan(steps: list[PlanStepDescriptor]) -> dict[str, Any]:
    """Persist a research plan for transparency/audit.

    Use this whenever you have a multi-step approach in mind. The user
    will see your plan in the UI but cannot approve/deny — you decide
    whether to proceed. Call this AGAIN any time you revise your
    approach; the old version is marked superseded.

    Max 5 plan versions per turn. Returns {plan_id, version, status}.
    """
    try:
        thread_id = current_thread_id()
        db_url = current_db_url()
    except MemoryContextNotBoundError as exc:
        slog.warning("agent.propose_plan.unbound", error=str(exc))
        return {"error": "agent_context_not_bound"}
    plan_json = {"steps": [s.model_dump() for s in steps]}
    result = propose_or_supersede_plan(thread_id, plan_json, db_url)
    if result.capped:
        return _capped_response(thread_id, result)
    return _drafted_response(thread_id, result, plan_json, len(steps))
