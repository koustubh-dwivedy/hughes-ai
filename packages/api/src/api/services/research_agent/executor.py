"""Sequential step executor — Phase 3 of deep research (HUG-213+).

HUG-213 (E1) lands step expansion. HUG-214 (E2) lands the sequential
loop: for each pending step, mark running → dispatch a worker →
update status → yield SSE events. HUG-218 (S2) will replace the
serial loop with `asyncio.gather`-style fan-out.

Worker fan-out happens via the HUG-217 wrapper which composes the
existing ReAct agent under a worker policy.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from nl_engine.logging import get_logger

from api.prometheus import (
    research_step_duration_seconds,
    research_steps_total,
)
from api.repo import research_steps as steps_repo
from api.services.research_agent.events import (
    step_completed_event,
    step_failed_event,
    step_started_event,
)
from api.services.research_agent.telemetry import (
    EVENT_STEP_COMPLETED,
    EVENT_STEP_CREATED,
    EVENT_STEP_FAILED,
    EVENT_STEP_STARTED,
    log_event,
)
from api.services.research_agent.worker import run_step_as_worker
from api.types.research import Plan, Step

_slog = get_logger().bind(component="research.executor")


def _now() -> datetime:
    return datetime.now(UTC)


def expand_plan_into_steps(plan: Plan, db_url: str) -> list[Step]:
    """Read plan.plan_json.plan and insert one research_steps row per
    entry. Emits `research.step.created` per row + bumps
    `hughes_research_steps_total{status=pending}` per row.

    Dependencies are NOT stored on the step row — they live in
    plan_json (single source of truth). HUG-218's parallel coordinator
    reads them from there. Documented decision.

    Idempotency: this function should be called exactly once per plan
    approval. If called twice, ordinal uniqueness in the schema will
    raise IntegrityError. The approve route guards against that
    indirectly via the `plan.status != 'approved'` check that gates
    the expansion call site.
    """
    steps_json: list[dict[str, Any]] = list(plan.plan_json.get("plan") or [])
    out: list[Step] = []
    for entry in steps_json:
        ordinal = int(entry["ordinal"])
        description = str(entry["description"])
        step = steps_repo.create_step(
            plan_id=plan.plan_id,
            ordinal=ordinal,
            description=description,
            db_url=db_url,
            status="pending",
        )
        log_event(
            EVENT_STEP_CREATED,
            plan_id=str(plan.plan_id),
            step_id=str(step.step_id),
            ordinal=ordinal,
            description_chars=len(description),
            dependencies=list(entry.get("dependencies") or []),
        )
        research_steps_total.labels(status="pending").inc()
        out.append(step)
    return out


# ---- HUG-214 (E2): sequential execution loop --------------------


def _mark_terminal(
    step: Step, *, status: str, started: datetime,
    db_url: str, elapsed: float, error: str | None,
) -> dict[str, Any]:
    """Common path for both success + failure transitions: write the
    status + completed_at, bump counter + histogram, emit event."""
    completed = _now()
    steps_repo.update_step_status(
        step.step_id, status, db_url, completed_at=completed,  # type: ignore[arg-type]
    )
    research_steps_total.labels(status=status).inc()
    research_step_duration_seconds.observe(elapsed)
    updated = step.model_copy(update={
        "status": status, "started_at": started, "completed_at": completed,
    })
    if error is None:
        log_event(EVENT_STEP_COMPLETED, step_id=str(step.step_id),
                  ordinal=step.ordinal, elapsed_sec=round(elapsed, 2))
        return step_completed_event(updated)
    log_event(EVENT_STEP_FAILED, step_id=str(step.step_id),
              ordinal=step.ordinal, error=error[:300])
    return step_failed_event(updated, error=error[:300])


async def _execute_one_step(
    step: Step, *, plan_context: str, db_url: str, llm: BaseChatModel,
    request_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Mark one step running → dispatch worker → mark complete/failed.
    Yields the start + terminal SSE events. Worker exceptions are
    caught here so subsequent steps still run."""
    started = _now()
    steps_repo.update_step_status(
        step.step_id, "running", db_url, started_at=started,
    )
    research_steps_total.labels(status="running").inc()
    log_event(EVENT_STEP_STARTED, step_id=str(step.step_id),
              ordinal=step.ordinal)
    yield step_started_event(step.model_copy(update={
        "status": "running", "started_at": started,
    }))
    t0 = time.perf_counter()
    try:
        finding = await run_step_as_worker(
            step=step, plan_context=plan_context,
            db_url=db_url, llm=llm, request_id=request_id,
        )
        if finding is None:
            raise RuntimeError("worker did not produce a finding")
    except Exception as exc:  # noqa: BLE001 — categorically catch
        yield _mark_terminal(
            step, status="failed", started=started, db_url=db_url,
            elapsed=time.perf_counter() - t0, error=str(exc),
        )
        return
    yield _mark_terminal(
        step, status="complete", started=started, db_url=db_url,
        elapsed=time.perf_counter() - t0, error=None,
    )


async def execute_plan_sequentially(
    *, plan_id: UUID, db_url: str, llm: BaseChatModel,
    plan_context: str = "", request_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Run every pending step under `plan_id` in ordinal order.

    Yields SSE events: one `research.step.started` + one terminal
    event (`completed` or `failed`) per step. Step failures do NOT
    abort the loop — siblings still run, mirroring Anthropic's
    pattern where each sub-question is independent.

    HUG-218 (S2) replaces the loop with `asyncio.gather` across
    dependency-ready batches; today's loop is the simplest possible
    end-to-end deep turn so the surface is small.
    """
    pending = [
        s for s in steps_repo.get_steps_for_plan(plan_id, db_url)
        if s.status == "pending"
    ]
    pending.sort(key=lambda s: s.ordinal)
    _slog.info(
        "executor.sequential_start",
        plan_id=str(plan_id), step_count=len(pending),
    )
    for step in pending:
        async for event in _execute_one_step(
            step, plan_context=plan_context, db_url=db_url,
            llm=llm, request_id=request_id,
        ):
            yield event
    _slog.info("executor.sequential_done", plan_id=str(plan_id))
