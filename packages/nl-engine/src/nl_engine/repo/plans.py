"""Lead-agent plan persistence (HUG-242).

`propose_or_supersede_plan` is the single entry point the `propose_plan`
tool uses. It is idempotent w.r.t. the lead's tool-call ordering: each
invocation marks any prior active version (`draft`/`approved`/`running`/
`proposed`) as `superseded` and inserts a new row at `max(version)+1`
with `status='proposed'`. The cap (`MAX_PLAN_VERSIONS`) bounds how many
revisions the lead may stack per turn — prevents runaway re-planning
when the model loops on itself.

The repo helper does the SELECT+UPDATE+INSERT atomically in one
transaction; the `(thread_id, version)` unique index makes the race
window for two concurrent inserts trivially detectable.

Lives in `nl_engine.repo` (not `api.repo`) because the calling tool is
in `nl_engine.agent` — the import-graph rules forbid nl_engine →
api. The api layer has its own helpers in `api.repo.research` for
serving HTTP GET endpoints (HUG-245 territory).
"""

from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

# Hard cap on plan revisions per turn. Picked at 5 from the planning
# discussion — the lead is expected to refine 1-2 times in a typical
# deep question; 5 leaves headroom for genuine complexity while
# bounding pathological loops.
MAX_PLAN_VERSIONS = 5

# Statuses that count as the "current active" plan version. When the
# lead calls propose_plan again, these get flipped to 'superseded'.
_ACTIVE_STATUSES = ("draft", "approved", "running", "proposed")


class ProposePlanResult(NamedTuple):
    """Result of a propose_plan persistence attempt.

    `capped` indicates the call was rejected because MAX_PLAN_VERSIONS
    has been reached. On `capped=True`, plan_id and version reflect the
    existing latest version (so the tool's error payload can include
    them for the UI / lead's own context)."""

    plan_id: UUID
    version: int
    capped: bool


def get_latest_plan_id(thread_id: UUID, db_url: str) -> UUID | None:
    """Return the plan_id of the highest-version plan under `thread_id`,
    or None if no plan exists yet.

    Used by the lead-agent memory tools (Fix C, 2026-05-17) to bind
    `read_memory` / `write_memory` to the currently-active research_plans
    row rather than a placeholder uuid4 that doesn't satisfy the FK on
    `research_lead_notes.plan_id`.
    """
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        row = _latest_plan_row(cur, thread_id)
    return row[0] if row is not None else None


def _latest_plan_row(cur: Any, thread_id: UUID) -> tuple[UUID, int] | None:
    cur.execute(
        "SELECT plan_id, version FROM research_plans"
        " WHERE thread_id = %s ORDER BY version DESC LIMIT 1",
        (str(thread_id),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return UUID(str(row[0])), int(row[1])


def _insert_proposed(
    cur: Any, thread_id: UUID, next_version: int, plan_json: dict[str, Any]
) -> UUID:
    cur.execute(
        "UPDATE research_plans SET status = 'superseded'"
        " WHERE thread_id = %s AND status = ANY(%s)",
        (str(thread_id), list(_ACTIVE_STATUSES)),
    )
    cur.execute(
        "INSERT INTO research_plans"
        " (thread_id, version, status, plan_json)"
        " VALUES (%s, %s, 'proposed', %s)"
        " RETURNING plan_id",
        (str(thread_id), next_version, Jsonb(plan_json)),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("research_plans INSERT...RETURNING returned no row")
    return UUID(str(row[0]))


def propose_or_supersede_plan(
    thread_id: UUID, plan_json: dict[str, Any], db_url: str
) -> ProposePlanResult:
    """Persist a new proposed plan version for the thread.

    Marks any prior active version superseded. Caps at MAX_PLAN_VERSIONS;
    over the cap, returns the existing latest plan with capped=True.
    """
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        latest = _latest_plan_row(cur, thread_id)
        current_version = latest[1] if latest else 0
        if current_version >= MAX_PLAN_VERSIONS:
            if latest is None:
                raise RuntimeError("cap reached without a latest plan row")
            return ProposePlanResult(
                plan_id=latest[0], version=current_version, capped=True
            )
        next_version = current_version + 1
        new_id = _insert_proposed(cur, thread_id, next_version, plan_json)
    return ProposePlanResult(plan_id=new_id, version=next_version, capped=False)
