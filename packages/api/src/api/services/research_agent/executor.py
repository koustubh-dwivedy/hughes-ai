"""Sequential step executor — Phase 3 of deep research (HUG-213+).

HUG-213 (E1) lands the first piece: when a plan is approved, expand
its `plan_json.steps` into typed `research_steps` rows. Later issues
add execution proper:
  HUG-214 (E2) — sequential dispatch via the worker wrapper.
  HUG-215 (E3) — finding persistence per step.
  HUG-216 (E4) — final synthesis via the existing ReAct agent.
  HUG-218 (S2) — swap sequential for parallel via asyncio.gather.

Today's surface area is intentionally small: one pure function +
its telemetry. The function is exposed so the approve route can call
it synchronously right after the status flip.
"""

from __future__ import annotations

from typing import Any

from api.prometheus import research_steps_total
from api.repo import research_steps as steps_repo
from api.services.research_agent.telemetry import EVENT_STEP_CREATED, log_event
from api.types.research import Plan, Step


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
