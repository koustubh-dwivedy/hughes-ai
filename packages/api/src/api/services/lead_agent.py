"""Autonomous lead-agent runner (HUG-244 + HUG-247 Phase B).

`stream_lead_turn` is the ONLY path `routes/threads.py` uses to serve
`POST /threads/{tid}/messages`. The legacy
planner/executor/synthesizer pipeline (HUG-247 Phase B) and the
`RESEARCH_LEAD_AGENT_ENABLED` feature flag have both been removed.

The lead is a single autonomous agent: it decides when to plan, when to
delegate to subagents, when to take notes, and when to synthesize. It
runs on the chat ReAct graph (`nl_engine.agent.graph.build_graph`) with
the extended `LEAD_AGENT_TOOLS` registry (propose_plan, run_subagent,
read_memory, write_memory in addition to the data tools).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import structlog.contextvars
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from nl_engine.agent.lead_agent_prompt import LEAD_AGENT_SYSTEM_PROMPT
from nl_engine.agent.memory_context import (
    bind_memory_context,
    reset_memory_context,
)
from nl_engine.agent.run_context import (
    bind_event_emitter,
    reset_event_emitter,
)
from nl_engine.agent.state import MAX_STEPS_PER_TURN
from nl_engine.agent.tools import LEAD_AGENT_TOOLS

from api.repo import threads as threads_repo
from api.services.agent_runner import run_agent_isolated
from api.services.agent_runner_chat import chat_process_message
from api.types.threads import ThreadMessage


def _make_sse_emitter(events: list[dict[str, Any]]) -> Any:
    """Build an event emitter that collects SSE-shaped events into a
    list. The list is drained by `stream_lead_turn` after each agent
    step so events emitted from tools (propose_plan / run_subagent /
    write_memory) reach the SSE channel."""

    def emit(name: str, payload: dict[str, Any]) -> None:
        import json

        events.append({"event": name, "data": json.dumps(payload, default=str)})

    return emit


async def stream_lead_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Lead-agent SSE producer. Mirrors `stream_user_turn` but uses
    `LEAD_AGENT_TOOLS` + `LEAD_AGENT_SYSTEM_PROMPT` and binds
    memory_context / run_context for the four lead-only tools.

    `plan_id` starts as a fresh UUID — propose_plan creates the real
    research_plans row keyed by `thread_id`, not this placeholder. The
    placeholder satisfies memory_context's API; memory keys are
    plan-scoped via the persisted plan_id, not this contextvar value.
    """
    threads_repo.append_message(
        thread_id=thread_id, role="user", db_url=db_url, content=user_content
    )
    structlog.contextvars.bind_contextvars(thread_id=str(thread_id))

    pending_events: list[dict[str, Any]] = []
    emitter = _make_sse_emitter(pending_events)
    memory_tokens = bind_memory_context(uuid4(), db_url, thread_id=thread_id)
    emitter_token = bind_event_emitter(emitter)

    # Pre-pend the lead system prompt as the first message so
    # ensure_system_prompt is a no-op (it bails when message[0] is
    # already a SystemMessage).
    extras = {"_lead_agent_run": True}
    initial_messages = [SystemMessage(content=LEAD_AGENT_SYSTEM_PROMPT)]
    extras["_initial_messages"] = initial_messages  # type: ignore[assignment]

    try:
        async for event in run_agent_isolated(
            thread_id=thread_id,
            user_input=user_content,
            history=history,
            db_url=db_url,
            llm=llm,
            process_message=chat_process_message,
            max_steps=MAX_STEPS_PER_TURN,
            request_id=request_id,
            initial_state_extras=extras,
            tools=LEAD_AGENT_TOOLS,
        ):
            # Flush any tool-emitted events before the agent's own event.
            while pending_events:
                yield pending_events.pop(0)
            yield event
        # Flush any remaining tool events on completion.
        while pending_events:
            yield pending_events.pop(0)
    finally:
        reset_event_emitter(emitter_token)
        reset_memory_context(memory_tokens)
        structlog.contextvars.unbind_contextvars("thread_id")
