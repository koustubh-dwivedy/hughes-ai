"""Plan abort endpoint + read-only audit GETs (HUG-247 Phase B).

HUG-247 removed `/approve` — the autonomous lead-agent architecture
has no user approval gate (the lead decides whether to proceed). Only
the kill-switch `/abort` survives, plus the GET endpoints the audit
panel consumes (`/plans/latest`, `/plans/.../steps`, `/findings`,
`/subagent-calls`, `/notes`).

Ownership: every endpoint authorizes the requesting user against the
thread that owns the plan. Wrong user → 403.

`/abort` is idempotent (re-aborting an aborted plan returns 200 with
the unchanged status) and emits a `research.plan.aborted` SSE event +
bumps a `hughes_research_plan_decisions_total` counter.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request

from api.prometheus import research_plan_decisions_total
from api.repo import research as research_repo
from api.repo import threads as threads_repo
from api.routes.threads import _user_id
from api.services.research_agent.events import plan_aborted_event
from api.services.research_agent.telemetry import (
    EVENT_PLAN_ABORTED,
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


@router.get("/threads/{thread_id}/plans/{plan_id}/subagent-calls")
def get_plan_subagent_calls_route(
    thread_id: UUID,
    plan_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    """List every run_subagent invocation under a plan (HUG-245).

    Frontend's `useGetSubagentCallsQuery` reads this. Returns
    `{"calls": [...]}` ordered by `started_at` ascending so the audit
    panel renders chronologically.
    """
    from api.repo import subagent_calls as sc_repo
    plan = _authorize_and_get_plan(
        thread_id, plan_id, request, x_hughes_user, x_hughes_session
    )
    calls = sc_repo.list_by_plan(plan.plan_id, request.app.state.db_url)
    return {"calls": calls}


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


def _transition_to_aborted(plan: Plan, request: Request) -> dict[str, Any]:
    """Flip plan status to 'aborted' (idempotent) + emit event."""
    db_url = request.app.state.db_url
    new_status: PlanStatus = "aborted"
    if plan.status != new_status:
        research_repo.update_plan_status(plan.plan_id, new_status, db_url)
        log_event(
            EVENT_PLAN_ABORTED, plan_id=str(plan.plan_id),
            thread_id=str(plan.thread_id),
            version=plan.version, status=new_status,
        )
        research_plan_decisions_total.labels(decision=new_status).inc()
        refreshed = research_repo.get_plan(plan.plan_id, db_url)
        if refreshed is None:  # pragma: no cover — just updated, must exist
            raise HTTPException(status_code=500, detail="plan vanished")
        plan = refreshed
    return plan_aborted_event(plan)


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
    return _transition_to_aborted(plan, request)
