"""Step expansion tests (HUG-213, E1).

`expand_plan_into_steps` is the synchronous bridge from "plan as
JSONB doc" → "steps as typed rows". Cover:
- Happy: N steps in plan_json → N rows in research_steps.
- Ordinal + description round-trip.
- All rows land with status='pending'.
- Telemetry counter `hughes_research_steps_total{status='pending'}`
  increments per row.
- Empty plan (defensive — shouldn't happen in production but the
  function should not crash).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import psycopg
import pytest
from api.prometheus import research_steps_total
from api.repo import research as research_repo
from api.repo import research_steps as steps_repo
from api.repo import threads as threads_repo
from api.services.research_agent.executor import expand_plan_into_steps

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    db_url = _db_url()
    sid = f"exec-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=sid)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM research_plans WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        cur.execute(
            "DELETE FROM threads WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        conn.commit()


def _seed_plan(thread_id: UUID, steps: list[dict[str, object]]) -> object:
    return research_repo.create_plan(
        thread_id=thread_id,
        plan_json={
            "route": "deep",
            "reason": "test",
            "research_question_summary": "test",
            "plan": steps,
        },
        db_url=_db_url(),
    )


def test_three_step_plan_expands_to_three_pending_rows(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(
        thread_id,
        [
            {"ordinal": 1, "description": "Pull A", "dependencies": []},
            {"ordinal": 2, "description": "Pull B", "dependencies": []},
            {"ordinal": 3, "description": "Compare", "dependencies": [1, 2]},
        ],
    )

    out = expand_plan_into_steps(plan, db_url)
    assert len(out) == 3
    assert {s.ordinal for s in out} == {1, 2, 3}
    assert all(s.status == "pending" for s in out)
    # Round-trip via repo to confirm rows really landed:
    persisted = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert len(persisted) == 3
    by_ord = {s.ordinal: s for s in persisted}
    assert by_ord[1].description == "Pull A"
    assert by_ord[3].description == "Compare"


def test_step_counter_increments_per_row(thread_id: UUID) -> None:
    db_url = _db_url()
    before = research_steps_total.labels(status="pending")._value.get()  # type: ignore[attr-defined]
    plan = _seed_plan(
        thread_id,
        [{"ordinal": i, "description": f"s{i}", "dependencies": []} for i in (1, 2)],
    )
    expand_plan_into_steps(plan, db_url)
    after = research_steps_total.labels(status="pending")._value.get()  # type: ignore[attr-defined]
    assert after == before + 2


def test_empty_plan_yields_no_rows(thread_id: UUID) -> None:
    """Defensive: a plan_json with an empty plan list shouldn't crash
    (production won't see this, but the function shouldn't be brittle)."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [])
    out = expand_plan_into_steps(plan, db_url)
    assert out == []
    persisted = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert persisted == []


def test_approve_creates_step_rows_end_to_end(thread_id: UUID) -> None:
    """Integration: hitting POST /approve creates the step rows via
    the executor wired into the route."""
    from api.main import app
    from fastapi.testclient import TestClient

    db_url = _db_url()
    plan = _seed_plan(
        thread_id,
        [
            {"ordinal": 1, "description": "x", "dependencies": []},
            {"ordinal": 2, "description": "y", "dependencies": [1]},
        ],
    )
    app.state.db_url = db_url
    # Look up the thread to fetch its user_id (created with sid==uid).
    thread = threads_repo.get_thread(thread_id, db_url)
    assert thread is not None
    headers = {"X-Hughes-User": thread.user_id, "X-Hughes-Session": thread.user_id}
    with TestClient(app) as c:
        resp = c.post(
            f"/threads/{thread_id}/plans/{plan.plan_id}/approve",
            headers=headers,
        )
    assert resp.status_code == 200, resp.text
    persisted = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert len(persisted) == 2
    assert all(s.status == "pending" for s in persisted)
