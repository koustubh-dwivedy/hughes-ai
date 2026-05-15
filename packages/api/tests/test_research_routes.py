"""Approve / abort endpoint tests (HUG-212, L5).

Mirrors the live-Postgres + TestClient pattern of
test_threads_route.py. Covers:
- Happy path: 200 + status flip + emitted event payload.
- Ownership: wrong user gets 403.
- Cross-thread plan id: 400 (plan does not belong to thread).
- Idempotency: re-approve already-approved plan returns 200, status
  unchanged.
- Missing thread / plan: 404.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import psycopg
import pytest
from api.main import app
from api.repo import research as research_repo
from api.repo import threads as threads_repo
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def client() -> Iterator[TestClient]:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    app.state.db_url = _DB_URL
    with TestClient(app) as c:
        yield c
    _cleanup()


def _cleanup() -> None:
    if not _DB_URL:
        return
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM research_plans WHERE thread_id IN ("
            "SELECT thread_id FROM threads WHERE session_id LIKE 'route-l5-%'"
            ")"
        )
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id IN ("
            "SELECT thread_id FROM threads WHERE session_id LIKE 'route-l5-%'"
            ")"
        )
        cur.execute(
            "DELETE FROM threads WHERE session_id LIKE 'route-l5-%'"
        )


def _seed_thread_with_plan(user_id: str) -> tuple[UUID, UUID]:
    db_url = _db_url()
    sid = f"route-l5-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=user_id)
    plan = research_repo.create_plan(
        thread_id=thread.thread_id,
        plan_json={
            "route": "deep",
            "plan": [
                {"ordinal": 1, "description": "x", "dependencies": []},
            ],
        },
        db_url=db_url,
    )
    return thread.thread_id, plan.plan_id


def _user_headers(uid: str) -> dict[str, str]:
    return {"X-Hughes-User": uid, "X-Hughes-Session": uid}


# ---- happy paths --------------------------------------------------


def test_approve_transitions_draft_to_approved(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_thread_with_plan(uid)
    resp = client.post(
        f"/threads/{tid}/plans/{pid}/approve", headers=_user_headers(uid)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["event"] == "research.plan.approved"
    plan = research_repo.get_plan(pid, _db_url())
    assert plan is not None
    assert plan.status == "approved"


def test_abort_transitions_draft_to_aborted(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_thread_with_plan(uid)
    resp = client.post(
        f"/threads/{tid}/plans/{pid}/abort", headers=_user_headers(uid)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["event"] == "research.plan.aborted"
    plan = research_repo.get_plan(pid, _db_url())
    assert plan is not None
    assert plan.status == "aborted"


# ---- ownership + idempotency + error paths -----------------------


def test_approve_by_wrong_user_returns_403(client: TestClient) -> None:
    owner = f"u-{uuid4().hex[:6]}"
    stranger = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_thread_with_plan(owner)
    resp = client.post(
        f"/threads/{tid}/plans/{pid}/approve",
        headers=_user_headers(stranger),
    )
    assert resp.status_code == 403


def test_approve_already_approved_is_idempotent(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_thread_with_plan(uid)
    r1 = client.post(
        f"/threads/{tid}/plans/{pid}/approve", headers=_user_headers(uid)
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/threads/{tid}/plans/{pid}/approve", headers=_user_headers(uid)
    )
    assert r2.status_code == 200
    plan = research_repo.get_plan(pid, _db_url())
    assert plan is not None
    assert plan.status == "approved"


def test_missing_thread_returns_404(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    resp = client.post(
        f"/threads/{uuid4()}/plans/{uuid4()}/approve",
        headers=_user_headers(uid),
    )
    assert resp.status_code == 404


def test_missing_plan_returns_404(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    db_url = _db_url()
    sid = f"route-l5-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=uid)
    resp = client.post(
        f"/threads/{thread.thread_id}/plans/{uuid4()}/approve",
        headers=_user_headers(uid),
    )
    assert resp.status_code == 404


# ---- HUG-210 (L3): GET endpoint smoke tests --------------------


def test_get_latest_plan_returns_persisted_plan(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_thread_with_plan(uid)
    resp = client.get(
        f"/threads/{tid}/plans/latest", headers=_user_headers(uid)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] is not None
    assert body["plan"]["plan_id"] == str(pid)


def test_get_latest_plan_no_plan_yields_null(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    db_url = _db_url()
    sid = f"route-l5-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=uid)
    resp = client.get(
        f"/threads/{thread.thread_id}/plans/latest",
        headers=_user_headers(uid),
    )
    assert resp.status_code == 200
    assert resp.json() == {"plan": None}


def test_get_plan_steps_returns_list(client: TestClient) -> None:
    from api.services.research_agent.executor import expand_plan_into_steps
    uid = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_thread_with_plan(uid)
    plan = research_repo.get_plan(pid, _db_url())
    assert plan is not None
    expand_plan_into_steps(plan, _db_url())
    resp = client.get(
        f"/threads/{tid}/plans/{pid}/steps", headers=_user_headers(uid)
    )
    assert resp.status_code == 200
    steps = resp.json()["steps"]
    assert len(steps) == 1
    assert steps[0]["ordinal"] == 1


def test_plan_belongs_to_different_thread_returns_400(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    tid_a, pid = _seed_thread_with_plan(uid)
    # Create a second thread owned by the same user.
    db_url = _db_url()
    sid_b = f"route-l5-{uuid4().hex[:8]}"
    thread_b = threads_repo.create_thread(sid_b, db_url, user_id=uid)
    # Request thread B + plan A → mismatch → 400.
    resp = client.post(
        f"/threads/{thread_b.thread_id}/plans/{pid}/approve",
        headers=_user_headers(uid),
    )
    assert resp.status_code == 400
