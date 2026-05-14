"""Turn coordinator entrypoint (HUG-205 + HUG-208).

The route layer (`api.routes.threads.post_message`) calls
`route_turn(...)` so the depth-decision logic can change without
churning the route layer. HUG-205 (F4) landed the entrypoint;
HUG-208 (L1) wires the planner LLM in.

Current behaviour (L1):
  1. Call `planner.draft_plan` as the FIRST node — depth decision
     happens inside the planner LLM, not via a separate classifier.
  2. If `route == "shallow"`: forward to today's `stream_user_turn`,
     user-visible behaviour is unchanged.
  3. If `route == "deep"`: log telemetry + plan size, then end the
     stream WITHOUT yielding SSE events. The frontend sees the
     connection close. This is the documented transitional state
     in HUG-208's acceptance criteria — L2 (plan persistence) and
     L5 (approve/abort) will fill in the deep-route user experience.
  4. If the planner itself errors: log + emit a single SSE `error`
     frame, then forward to `stream_user_turn` so the user still
     gets *some* answer (graceful degradation).

Worth flagging: every turn now pays one extra LLM call (the
planner). That's the cost of having a single unified entrypoint
that decides depth at planner time. No flag-gating for now —
landing the telemetry early informs L2's UX design.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel

from api.prometheus import (
    research_plan_size_steps,
    research_plan_versions_total,
    research_turns_total,
)
from api.repo import research as research_repo
from api.services.agent_runner import stream_user_turn
from api.services.research_agent.events import plan_drafted_event
from api.services.research_agent.planner import (
    PlannerError,
    draft_plan,
)
from api.services.research_agent.telemetry import (
    EVENT_TURN_ROUTED,
    log_event,
)
from api.types.threads import ThreadMessage

_PLANNER_ERROR_PAYLOAD = json.dumps(
    {
        "message": (
            "Planner couldn't classify the question; "
            "falling back to a single-shot answer."
        )
    }
)


async def _forward_shallow(
    *,
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str,
) -> AsyncIterator[dict[str, Any]]:
    async for event in stream_user_turn(
        thread_id=thread_id,
        user_content=user_content,
        db_url=db_url,
        llm=llm,
        history=history,
        request_id=request_id,
    ):
        yield event


async def _persist_and_emit_deep_plan(
    thread_id: UUID, draft: Any, db_url: str
) -> dict[str, Any]:
    """HUG-209: write the draft to research_plans + return the SSE
    event the coordinator should yield. Splits out the deep-branch
    body so `route_turn` stays under the structural line cap."""
    plan = research_repo.create_plan(
        thread_id=thread_id,
        plan_json=draft.model_dump(mode="json"),
        db_url=db_url,
    )
    research_plan_versions_total.inc()
    return plan_drafted_event(plan)


async def route_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Unified entrypoint for every user turn. Calls the planner LLM
    first; routes by its verdict. Returns the same AsyncIterator
    contract as `stream_user_turn` so the route layer is stable
    across phases."""
    try:
        draft = draft_plan(user_content, history, llm)
    except PlannerError as exc:
        log_event(
            EVENT_TURN_ROUTED, route="shallow", reason="planner_failed",
            thread_id=str(thread_id), error=str(exc)[:300],
        )
        research_turns_total.labels(route="shallow").inc()
        yield {"event": "error", "data": _PLANNER_ERROR_PAYLOAD}
        async for event in _forward_shallow(
            thread_id=thread_id, user_content=user_content, db_url=db_url,
            llm=llm, history=history, request_id=request_id,
        ):
            yield event
        return

    log_event(
        EVENT_TURN_ROUTED, route=draft.route, reason=draft.reason[:160],
        thread_id=str(thread_id),
    )
    research_turns_total.labels(route=draft.route).inc()
    if draft.plan is not None:
        research_plan_size_steps.observe(len(draft.plan))

    if draft.route == "shallow":
        async for event in _forward_shallow(
            thread_id=thread_id, user_content=user_content, db_url=db_url,
            llm=llm, history=history, request_id=request_id,
        ):
            yield event
        return

    # Deep route (HUG-209): persist + emit research.plan.drafted. Stream
    # ends after the event for now; HUG-211/HUG-212 fill in the UI + the
    # approve/abort handoff.
    yield await _persist_and_emit_deep_plan(thread_id, draft, db_url)
