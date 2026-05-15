"""Worker invocation wrapper (HUG-217, S1).

A worker IS the existing ReAct agent (5 tools, ANCHOR-A-through-E
system prompt, DSPy-compiled artefacts, full 24/24 must-pass eval
discipline) invoked via the `run_agent_isolated` primitive with four
narrow policy overrides:

  1. `history=[]` — each worker is context-isolated. The full chat
     history would just dilute the worker's attention budget; the
     coordinator passes the worker's per-step description as the
     entire user input.
  2. `process_message` — worker-specific callback that persists
     `final_answer` payloads to `research_findings` instead of
     `thread_messages` (see `worker_process_message.py`).
  3. `max_steps` — tighter cap than the chat path (default 5 vs 10).
     A worker's job is one focused sub-question; a 5-step ReAct loop
     is generous.
  4. `initial_state_extras={"step_id": ...}` — threads the step ID
     through the agent state so anywhere downstream can log it via
     `AgentState.slots`.

Today's contract: the wrapper drives the worker to completion,
swallows the emitted SSE events (workers don't surface to the chat
stream), and returns the persisted `Finding` row. The coordinator
calls one of these per step; HUG-218 swaps the loop for
`asyncio.gather` to parallelize.

This module deliberately tiny — every reusable concern lives one
layer down. Adding a tool, changing the prompt, swapping the LLM
provider all happen elsewhere; the worker just composes.
"""

from __future__ import annotations

import time
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from nl_engine.logging import get_logger

from api.prometheus import (
    research_subagent_spawns_total,
)
from api.repo import research_steps as steps_repo
from api.services.agent_runner import run_agent_isolated
from api.services.research_agent.telemetry import (
    EVENT_SUBAGENT_COMPLETED,
    EVENT_SUBAGENT_FAILED,
    EVENT_SUBAGENT_SPAWNED,
    log_event,
)
from api.services.research_agent.worker_process_message import (
    make_worker_process_message,
)
from api.types.research import Finding, Step

_DEFAULT_MAX_STEPS = 5

_slog = get_logger().bind(component="research.worker")


def _format_worker_input(step: Step, plan_context: str) -> str:
    """Compose the user message the ReAct agent receives. Plan
    context (e.g. the lead's notes so far) sits above the step's
    own description so the agent has both the local task and the
    broader why."""
    if plan_context:
        return (
            f"PLAN CONTEXT:\n{plan_context}\n\n"
            f"YOUR STEP (ordinal {step.ordinal}):\n{step.description}"
        )
    return f"YOUR STEP (ordinal {step.ordinal}):\n{step.description}"


async def _drain_agent(
    *, step: Step, user_input: str, db_url: str,
    llm: BaseChatModel, max_steps: int, request_id: str,
) -> None:
    """Run the worker agent to completion, swallowing the emitted SSE
    events (workers don't surface to the chat stream)."""
    process_msg = make_worker_process_message(step_id=step.step_id)
    async for _event in run_agent_isolated(
        thread_id=step.step_id,
        user_input=user_input,
        history=[],
        db_url=db_url,
        llm=llm,
        process_message=process_msg,
        max_steps=max_steps,
        request_id=request_id,
        initial_state_extras={"step_id": str(step.step_id)},
    ):
        pass


async def run_step_as_worker(
    *,
    step: Step,
    plan_context: str,
    db_url: str,
    llm: BaseChatModel,
    request_id: str = "",
    max_steps: int = _DEFAULT_MAX_STEPS,
) -> Finding | None:
    """Drive one worker turn end-to-end. Returns the persisted
    finding row, or None if the agent finished without firing
    `final_answer` (step is implicitly failed — caller marks status)."""
    subagent_id = uuid4()
    research_subagent_spawns_total.inc()
    log_event(
        EVENT_SUBAGENT_SPAWNED, subagent_id=str(subagent_id),
        step_id=str(step.step_id), ordinal=step.ordinal, max_steps=max_steps,
    )
    t0 = time.perf_counter()
    try:
        await _drain_agent(
            step=step,
            user_input=_format_worker_input(step, plan_context),
            db_url=db_url, llm=llm,
            max_steps=max_steps, request_id=request_id,
        )
    except Exception as exc:  # noqa: BLE001 — surface as failed event
        log_event(
            EVENT_SUBAGENT_FAILED, subagent_id=str(subagent_id),
            step_id=str(step.step_id), error=str(exc)[:300],
            elapsed_sec=round(time.perf_counter() - t0, 2),
        )
        raise
    findings = steps_repo.get_findings_for_step(step.step_id, db_url)
    finding = findings[-1] if findings else None
    log_event(
        EVENT_SUBAGENT_COMPLETED, subagent_id=str(subagent_id),
        step_id=str(step.step_id),
        finding_id=str(finding.finding_id) if finding else None,
        elapsed_sec=round(time.perf_counter() - t0, 2),
    )
    return finding
