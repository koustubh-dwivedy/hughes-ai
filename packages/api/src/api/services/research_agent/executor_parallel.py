"""Parallel step executor — HUG-218 (S2).

Swaps the sequential loop in `executor.execute_plan_sequentially`
for a dependency-aware parallel dispatcher. Reads the plan's
`plan_json["plan"]` for dependency edges (single source of truth per
the HUG-213 decision), groups ready steps into batches, and runs
each batch via `asyncio.gather` with a `Semaphore` cap.

Default `MAX_PARALLEL=3` per Anthropic's "3-5 is the sweet spot"
finding. The sequential path remains in `executor.py` as the
documented fallback; passing `max_parallel=1` to this function
produces equivalent serial behaviour.

Dependency-graph rules:
- A step is READY when all its `dependencies` ordinals are in a
  terminal state (`complete` or `failed`).
- A step's siblings can run before/after it freely.
- A failed dependency does NOT block downstream steps — workers
  are independent and the lead's synthesizer will decide later
  whether the partial result is usable. (Matches Anthropic's
  "siblings still run on failure" decision from E2.)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from nl_engine.logging import get_logger

from api.prometheus import research_parallel_batch_size
from api.repo import research as research_repo
from api.repo import research_steps as steps_repo
from api.services.research_agent.executor import _execute_one_step
from api.types.research import Step

_DEFAULT_MAX_PARALLEL = 3
_TERMINAL_STATUSES = frozenset({"complete", "failed"})

_slog = get_logger().bind(component="research.parallel")


def _deps_by_ordinal(plan_json: dict[str, Any]) -> dict[int, list[int]]:
    """Build {ordinal: [dep_ordinals]} from plan_json. Missing entries
    default to empty (no deps)."""
    out: dict[int, list[int]] = {}
    for entry in plan_json.get("plan") or []:
        ord_ = int(entry["ordinal"])
        out[ord_] = [int(d) for d in (entry.get("dependencies") or [])]
    return out


def _ready_steps(
    pending: list[Step], deps_map: dict[int, list[int]],
    terminal_ordinals: set[int],
) -> list[Step]:
    """Steps whose dependencies are all terminal."""
    return [
        s for s in pending
        if all(d in terminal_ordinals for d in deps_map.get(s.ordinal, []))
    ]


async def _run_one_capped(
    sem: asyncio.Semaphore, step: Step, *,
    plan_context: str, db_url: str, llm: BaseChatModel, request_id: str,
) -> list[dict[str, Any]]:
    """Drain one worker under the concurrency cap; return all events."""
    async with sem:
        out: list[dict[str, Any]] = []
        async for event in _execute_one_step(
            step, plan_context=plan_context, db_url=db_url,
            llm=llm, request_id=request_id,
        ):
            out.append(event)
        return out


async def _run_one_batch(
    ready: list[Step], sem: asyncio.Semaphore,
    *, plan_context: str, db_url: str, llm: BaseChatModel, request_id: str,
) -> list[dict[str, Any]]:
    """Dispatch a batch of ready steps concurrently; flatten + return
    their accumulated events in completion order."""
    research_parallel_batch_size.observe(len(ready))
    coros = [
        _run_one_capped(
            sem, s, plan_context=plan_context, db_url=db_url,
            llm=llm, request_id=request_id,
        )
        for s in ready
    ]
    results = await asyncio.gather(*coros, return_exceptions=False)
    return [ev for events in results for ev in events]


async def execute_plan_parallel(
    *, plan_id: UUID, db_url: str, llm: BaseChatModel,
    plan_context: str = "", request_id: str = "",
    max_parallel: int = _DEFAULT_MAX_PARALLEL,
) -> AsyncIterator[dict[str, Any]]:
    """Run every pending step under `plan_id` in dependency order,
    parallelizing batches of independent steps up to `max_parallel`.

    Yields the same SSE event types as the sequential path —
    started + terminal per step. Within a batch, events fire in
    completion order, not ordinal order. Step failure does not
    abort the loop. See `_run_one_batch` for the actual gather call.
    """
    plan = research_repo.get_plan(plan_id, db_url)
    if plan is None:
        return
    deps_map = _deps_by_ordinal(plan.plan_json)
    all_steps = steps_repo.get_steps_for_plan(plan_id, db_url)
    pending = [s for s in all_steps if s.status == "pending"]
    terminal_ordinals = {
        s.ordinal for s in all_steps if s.status in _TERMINAL_STATUSES
    }
    sem = asyncio.Semaphore(max_parallel)
    _slog.info(
        "parallel.start", plan_id=str(plan_id),
        step_count=len(pending), max_parallel=max_parallel,
    )
    while pending:
        ready = _ready_steps(pending, deps_map, terminal_ordinals)
        if not ready:
            _slog.warning(
                "parallel.deadlock", plan_id=str(plan_id),
                remaining=[s.ordinal for s in pending],
            )
            break
        for ev in await _run_one_batch(
            ready, sem, plan_context=plan_context,
            db_url=db_url, llm=llm, request_id=request_id,
        ):
            yield ev
        for s in ready:
            terminal_ordinals.add(s.ordinal)
        pending = [s for s in pending if s.ordinal not in terminal_ordinals]
    _slog.info("parallel.done", plan_id=str(plan_id))
