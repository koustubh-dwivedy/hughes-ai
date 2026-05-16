"""Plan approve / abort endpoints (HUG-212, L5).

Two routes, both under `/threads/{thread_id}/plans/{plan_id}/...`:
  POST .../approve  — plan.status: draft → approved
  POST .../abort    — plan.status: draft → aborted

Ownership: the plan's thread must belong to the requesting user
(same `_user_id` helper as routes/threads.py). Wrong user → 403.

Both endpoints are idempotent: re-approving an already-approved plan
returns 200 with the unchanged status.

The state transition emits a structlog event + bumps a
`hughes_research_plan_decisions_total` counter, then yields the
typed `Plan` row back to the caller. The frontend's mutation hook
(HUG-210, L3) invalidates the `ResearchPlan` tag on success.

Execution (HUG-213, E1 onwards) hooks off the `research.plan.approved`
SSE event downstream — those land in later issues; for now we just
flip the status + announce it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request

from api.prometheus import research_plan_decisions_total
from api.repo import research as research_repo
from api.repo import threads as threads_repo
from api.routes.threads import _user_id
from api.services.research_agent.events import (
    plan_aborted_event,
    plan_approved_event,
)
from api.services.research_agent.executor import expand_plan_into_steps
from api.services.research_agent.telemetry import (
    EVENT_PLAN_ABORTED,
    EVENT_PLAN_APPROVED,
    log_event,
)
from api.types.research import Plan, PlanStatus

router = APIRouter()


# ---- HUG-210 (L3): GET endpoints the frontend RTK Query slice
# consumes to render plan-preview + step-list + findings + notes.


@router.get("/threads/{thread_id}/plans/latest")
def get_latest_plan_route(
    thread_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    db_url = request.app.state.db_url
    thread = threads_repo.get_thread(thread_id, db_url)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    if thread.user_id != _user_id(x_hughes_user, x_hughes_session):
        raise HTTPException(status_code=403, detail="not your thread")
    plan = research_repo.get_latest_plan(thread_id, db_url)
    if plan is None:
        return {"plan": None}
    return {"plan": plan.model_dump(mode="json")}


@router.get("/threads/{thread_id}/plans/{plan_id}/steps")
def get_plan_steps_route(
    thread_id: UUID,
    plan_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    from api.repo import research_steps as steps_repo
    plan = _authorize_and_get_plan(
        thread_id, plan_id, request, x_hughes_user, x_hughes_session
    )
    steps = steps_repo.get_steps_for_plan(plan.plan_id, request.app.state.db_url)
    return {"steps": [s.model_dump(mode="json") for s in steps]}


@router.get("/threads/{thread_id}/plans/{plan_id}/findings")
def get_plan_findings_route(
    thread_id: UUID,
    plan_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    from api.repo import research_steps as steps_repo
    plan = _authorize_and_get_plan(
        thread_id, plan_id, request, x_hughes_user, x_hughes_session
    )
    findings = steps_repo.get_findings_for_plan(
        plan.plan_id, request.app.state.db_url
    )
    return {"findings": [f.model_dump(mode="json") for f in findings]}


@router.get("/threads/{thread_id}/plans/{plan_id}/notes")
def get_plan_notes_route(
    thread_id: UUID,
    plan_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    plan = _authorize_and_get_plan(
        thread_id, plan_id, request, x_hughes_user, x_hughes_session
    )
    notes = research_repo.list_lead_notes(
        plan.plan_id, request.app.state.db_url
    )
    return {"notes": [n.model_dump(mode="json") for n in notes]}


def _authorize_and_get_plan(
    thread_id: UUID, plan_id: UUID, request: Request,
    x_hughes_user: str | None, x_hughes_session: str | None,
) -> Plan:
    """Shared check: requesting user owns the thread that owns the plan.

    Raises HTTPException(404) when the thread or plan is missing,
    (403) when the requesting user doesn't own the thread, (400) when
    the plan_id and thread_id don't match. Returns the Plan dataclass
    on success."""
    db_url = request.app.state.db_url
    thread = threads_repo.get_thread(thread_id, db_url)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    uid = _user_id(x_hughes_user, x_hughes_session)
    if thread.user_id != uid:
        raise HTTPException(status_code=403, detail="not your thread")
    plan = research_repo.get_plan(plan_id, db_url)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")
    if plan.thread_id != thread_id:
        raise HTTPException(status_code=400, detail="plan does not belong to thread")
    return plan


def _decide(
    *, plan: Plan, new_status: PlanStatus,
    request: Request,
    event_builder: Callable[[Plan], dict[str, Any]],
    event_name: str,
) -> dict[str, Any]:
    """Transition the plan to `new_status` if it isn't already there;
    emit the corresponding event + telemetry. Idempotent."""
    db_url = request.app.state.db_url
    if plan.status != new_status:
        research_repo.update_plan_status(plan.plan_id, new_status, db_url)
        log_event(
            event_name, plan_id=str(plan.plan_id),
            thread_id=str(plan.thread_id),
            version=plan.version, status=new_status,
        )
        research_plan_decisions_total.labels(decision=new_status).inc()
        # Re-read so the SSE payload reflects the new status.
        refreshed = research_repo.get_plan(plan.plan_id, db_url)
        if refreshed is None:  # pragma: no cover — just updated, must exist
            raise HTTPException(status_code=500, detail="plan vanished")
        plan = refreshed
    return event_builder(plan)


@router.post("/threads/{thread_id}/plans/{plan_id}/approve")
def approve_plan(
    thread_id: UUID,
    plan_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    """LEGACY (HUG-246): plan approval no longer exists in the autonomous
    lead-agent architecture — the lead decides whether to proceed without
    user approval. This route survives only for the legacy
    planner/executor/synthesizer pipeline that runs when
    `RESEARCH_LEAD_AGENT_ENABLED=0`. HUG-247 deletes this route entirely
    when the legacy pipeline is decommissioned.
    """
    plan = _authorize_and_get_plan(
        thread_id, plan_id, request, x_hughes_user, x_hughes_session
    )
    # HUG-213 (E1): expand plan_json.steps into research_steps on the
    # FIRST approve. Guarded by the status check so a re-approve is
    # still idempotent — no duplicate step rows.
    if plan.status != "approved":
        expand_plan_into_steps(plan, request.app.state.db_url)
    return _decide(
        plan=plan, new_status="approved", request=request,
        event_builder=plan_approved_event, event_name=EVENT_PLAN_APPROVED,
    )


@router.post("/threads/{thread_id}/plans/{plan_id}/abort")
def abort_plan(
    thread_id: UUID,
    plan_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    """Kill-switch for a running research plan (HUG-246).

    In both architectures this marks the plan as aborted. The legacy
    pipeline checks `plan.status == 'aborted'` between steps and halts.
    The autonomous lead-agent path (HUG-244) doesn't poll plan status
    today — abort is best-effort: it stops the persistence side of the
    flow but the in-flight LangGraph invocation keeps running until it
    voluntarily terminates. A future enhancement (post-HUG-247) is to
    bridge `asyncio.Task.cancel()` into the running graph for hard
    cancellation; for now the recommendation is to let the lead's
    current step finish, then ignore subsequent output for an aborted
    plan_id at the frontend.

    Idempotent: re-aborting an already-aborted plan returns 200 with
    the same payload.
    """
    plan = _authorize_and_get_plan(
        thread_id, plan_id, request, x_hughes_user, x_hughes_session
    )
    return _decide(
        plan=plan, new_status="aborted", request=request,
        event_builder=plan_aborted_event, event_name=EVENT_PLAN_ABORTED,
    )
