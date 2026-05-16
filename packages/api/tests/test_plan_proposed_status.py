"""Regression tests for PlanStatus literal accepting 'proposed' (E2E
verification 2026-05-17 found that HUG-241's migration 017 added
'proposed' to the SQL CHECK but never updated the Pydantic literal.
Every plan read after `propose_plan` would 500.)

Tests:
- `_row_to_plan` accepts a row with status='proposed' without raising.
- `get_plan` round-trips a proposed plan.
- `/abort` on a plan whose status is 'proposed' returns 200 (not 500).
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

pytestmark = pytest.mark.db

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
        cur.execute("DELETE FROM threads WHERE session_id LIKE 'proposed-test-%'")


def _seed_proposed_plan(uid: str) -> tuple[UUID, UUID]:
    """Insert a thread + research_plans row with status='proposed'."""
    url = _db_url()
    sid = f"proposed-test-{uuid4().hex[:6]}"
    thread = threads_repo.create_thread(sid, url, user_id=uid)
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO research_plans (thread_id, version, status, plan_json)"
            " VALUES (%s, 1, 'proposed', '{}'::jsonb)"
            " RETURNING plan_id",
            (str(thread.thread_id),),
        )
        row = cur.fetchone()
        assert row is not None  # noqa: S101 — test invariant
    return thread.thread_id, UUID(str(row[0]))


def test_row_to_plan_accepts_proposed_status() -> None:
    """Direct call to `get_plan` returns a Plan object — must not raise
    Pydantic ValidationError on status='proposed'."""
    uid = f"u-{uuid4().hex[:6]}"
    _, pid = _seed_proposed_plan(uid)
    plan = research_repo.get_plan(pid, _db_url())
    assert plan is not None
    assert plan.status == "proposed"


def test_get_latest_plan_works_when_latest_is_proposed(client: TestClient) -> None:
    """`/threads/{tid}/plans/latest` must not 500 when the latest plan
    is in status 'proposed' (the default for propose_plan output)."""
    uid = f"u-{uuid4().hex[:6]}"
    tid, _pid = _seed_proposed_plan(uid)
    resp = client.get(
        f"/threads/{tid}/plans/latest",
        headers={"X-Hughes-User": uid, "X-Hughes-Session": "proposed-sess"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plan"]["status"] == "proposed"


def test_abort_on_proposed_plan_transitions_to_aborted(client: TestClient) -> None:
    """The bug was: /abort on proposed plan → 500 (Pydantic
    ValidationError). After fix, /abort transitions proposed → aborted."""
    uid = f"u-{uuid4().hex[:6]}"
    tid, pid = _seed_proposed_plan(uid)
    resp = client.post(
        f"/threads/{tid}/plans/{pid}/abort",
        headers={"X-Hughes-User": uid, "X-Hughes-Session": "proposed-sess"},
    )
    assert resp.status_code == 200, resp.text
    plan = research_repo.get_plan(pid, _db_url())
    assert plan is not None
    assert plan.status == "aborted"
