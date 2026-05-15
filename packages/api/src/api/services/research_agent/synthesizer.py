"""Final synthesis via the existing ReAct agent (HUG-216, E4).

When every step in a plan reaches a terminal state, the lead's last
job is one more LLM call: read the collected findings, write the
user-facing answer. That last call IS the existing ReAct agent
invoked via `run_agent_isolated` with synthesis-shaped input:

  - user_input: the user's original question + a compact rendering
    of each finding's summary + rows.
  - history: [] — the worker findings ARE the context.
  - process_message: chat-shaped callback so the answer lands in
    thread_messages (the user wants to see it in their chat) and
    the existing final_answer tool produces the same payload shape
    as a chat turn (OpenUI DSL included).

After the synthesis turn yields a `final` event, transition the
plan to `complete` and yield a `research.turn.completed` SSE event.

This module is intentionally thin — every reusable concern lives
elsewhere. The agent, the tools, the OpenUI validator, the
persistence callbacks are all unchanged. The synthesis is JUST
another invocation with different input shape.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from nl_engine.logging import get_logger

from api.prometheus import research_turn_duration_seconds
from api.repo import research as research_repo
from api.repo import research_steps as steps_repo
from api.services.agent_runner import run_agent_isolated
from api.services.agent_runner_chat import chat_process_message
from api.services.research_agent.telemetry import (
    EVENT_TURN_COMPLETED,
    log_event,
)
from api.types.research import Finding

_slog = get_logger().bind(component="research.synthesizer")


def _format_finding(f: Finding) -> str:
    """Compact human-readable rendering of one finding. Keeps the
    synthesis prompt bounded — long findings get their full payload
    elided in favour of summary + first 5 rows."""
    parts = [f"FINDING (step_id={str(f.step_id)[:8]}…):"]
    if f.summary_text:
        parts.append(f"summary: {f.summary_text}")
    if f.structured_rows_json:
        rows_preview = f.structured_rows_json[:5]
        suffix = "" if len(f.structured_rows_json) <= 5 else " (truncated)"
        parts.append(f"rows: {rows_preview}{suffix}")
    if f.mf_query_json:
        parts.append(f"mf_query: {f.mf_query_json}")
    return "\n".join(parts)


def _format_synthesis_input(
    user_question: str, findings: list[Finding]
) -> str:
    """The 'user message' the synthesis agent receives. Anthropic-
    pattern: original question + a digest of each finding. The
    agent's existing system prompt (ANCHOR-A through ANCHOR-E)
    already knows how to render an answer; the findings are just
    the data."""
    if not findings:
        return (
            f"USER QUESTION: {user_question}\n\n"
            "No findings were collected (all steps failed or were "
            "aborted). Acknowledge this in `final_answer` with a brief "
            "summary; rows + mf_query can be empty."
        )
    findings_text = "\n\n".join(_format_finding(f) for f in findings)
    return (
        f"USER QUESTION: {user_question}\n\n"
        f"FINDINGS FROM SUBAGENT WORKERS:\n\n{findings_text}\n\n"
        "Synthesize the findings into ONE answer for the user via the "
        "`final_answer` tool. Use OpenUI DSL when a chart/table would "
        "communicate the answer better than prose. Don't re-run any "
        "metric queries — trust the findings."
    )


async def synthesize_final_answer(
    *,
    plan_id: UUID,
    thread_id: UUID,
    user_question: str,
    db_url: str,
    llm: BaseChatModel,
    request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Drive the synthesis turn end-to-end. Yields the chat-shaped
    SSE events from the underlying agent (`thinking`, `step`,
    `final`); after the agent terminates, transitions the plan to
    `complete` and yields `research.turn.completed`."""
    t0 = time.perf_counter()
    findings = steps_repo.get_findings_for_plan(plan_id, db_url)
    synthesis_input = _format_synthesis_input(user_question, findings)
    _slog.info(
        "synthesizer.start", plan_id=str(plan_id),
        findings_count=len(findings),
        prompt_chars=len(synthesis_input),
    )
    async for event in run_agent_isolated(
        thread_id=thread_id,
        user_input=synthesis_input,
        history=[],
        db_url=db_url,
        llm=llm,
        process_message=chat_process_message,
        request_id=request_id,
    ):
        yield event
    elapsed = time.perf_counter() - t0
    research_repo.update_plan_status(plan_id, "complete", db_url)
    research_turn_duration_seconds.observe(elapsed)
    log_event(
        EVENT_TURN_COMPLETED, plan_id=str(plan_id),
        thread_id=str(thread_id),
        findings_count=len(findings),
        elapsed_sec=round(elapsed, 2),
    )
    yield {
        "event": "research.turn.completed",
        "data": (
            '{"plan_id": "' + str(plan_id) + '", "status": "complete"}'
        ),
    }
