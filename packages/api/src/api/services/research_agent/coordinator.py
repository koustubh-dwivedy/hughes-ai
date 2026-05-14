"""Turn coordinator entrypoint (HUG-205, F4).

The route layer (`api.routes.threads.post_message`) calls
`route_turn(...)` instead of `stream_user_turn(...)` directly so the
depth-decision logic landing in HUG-208 (L1, planner) can swap the
body without touching the route layer.

In F4 the coordinator is a thin wrapper: it logs a
`research.turn.routed` event with `route="shallow"` /
`reason="phase-1-default"`, bumps the per-route counter, then
delegates byte-identically to `stream_user_turn`. User-visible
behaviour is unchanged.

When L1 lands, this function becomes:

    plan_draft = await planner.draft_plan(...)
    if plan_draft.route == "shallow":
        log_event(EVENT_TURN_ROUTED, route="shallow", reason=plan_draft.reason)
        async for event in stream_user_turn(...):
            yield event
    else:
        log_event(EVENT_TURN_ROUTED, route="deep", reason=plan_draft.reason)
        # Persist plan (HUG-209, L2), wait for approval (HUG-212, L5),
        # then execute via subagents (E1-E4, S1-S2). All inside the same
        # SSE stream — the route layer doesn't care which branch ran.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel

from api.prometheus import research_turns_total
from api.services.agent_runner import stream_user_turn
from api.services.research_agent.telemetry import (
    EVENT_TURN_ROUTED,
    log_event,
)
from api.types.threads import ThreadMessage


async def route_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Unified entrypoint for every user turn. Returns the same
    AsyncIterator over SSE event dicts as `stream_user_turn`, so the
    route layer's contract with `EventSourceResponse` doesn't shift
    as the depth-decision logic lands in later phases.

    Today: always routes to the existing ReAct agent (shallow path)
    and emits one telemetry event so we can already chart shallow/
    deep ratio once the planner ships.
    """
    log_event(
        EVENT_TURN_ROUTED,
        route="shallow",
        reason="phase-1-default",
        thread_id=str(thread_id),
    )
    research_turns_total.labels(route="shallow").inc()
    async for event in stream_user_turn(
        thread_id=thread_id,
        user_content=user_content,
        db_url=db_url,
        llm=llm,
        history=history,
        request_id=request_id,
    ):
        yield event
