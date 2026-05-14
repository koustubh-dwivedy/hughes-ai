"""Round-trip tests for the research repo (HUG-203).

Exercises every public function in `api.repo.research` against a
live Postgres. Mirrors the integration-tier pattern of
`test_threads_repo.py` — each test seeds its own thread + cleans
up implicitly via FK cascade when the parent thread is deleted at
teardown.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import research as repo
from api.repo import research_steps as steps_repo
from api.repo import threads as threads_repo


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set; research-repo tests need Postgres")
    return url


@pytest.fixture
def thread_id() -> UUID:
    """Seed a throwaway thread for FK targeting. Teardown deletes
    the thread which cascades-deletes any research_* rows under it."""
    db_url = _db_url()
    sid = f"pytest-research-repo-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM threads WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        conn.commit()


# ============================================================
# RESEARCH_PLANS
# ============================================================


def test_create_plan_auto_version_starts_at_one(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {"steps": []}, db_url)
    assert plan.thread_id == thread_id
    assert plan.version == 1
    assert plan.status == "draft"
    assert plan.plan_json == {"steps": []}


def test_create_plan_jsonb_round_trips(thread_id: UUID) -> None:
    db_url = _db_url()
    payload = {"steps": [{"ordinal": 1, "description": "fetch metrics"}]}
    plan = repo.create_plan(thread_id, payload, db_url)
    fetched = repo.get_latest_plan(thread_id, db_url)
    assert fetched is not None
    assert fetched.plan_id == plan.plan_id
    assert fetched.plan_json == payload


def test_get_latest_plan_returns_highest_version(thread_id: UUID) -> None:
    db_url = _db_url()
    p1 = repo.create_plan(thread_id, {"v": 1}, db_url)
    p2 = repo.create_plan(thread_id, {"v": 2}, db_url)
    p3 = repo.create_plan(thread_id, {"v": 3}, db_url)
    latest = repo.get_latest_plan(thread_id, db_url)
    assert latest is not None
    assert latest.plan_id == p3.plan_id
    assert latest.version == 3
    assert p1.version == 1 and p2.version == 2


def test_get_latest_plan_returns_none_for_unknown_thread() -> None:
    """No exception — just None — when a thread has no plans."""
    db_url = _db_url()
    assert repo.get_latest_plan(uuid4(), db_url) is None


def test_list_plan_versions_newest_first(thread_id: UUID) -> None:
    db_url = _db_url()
    repo.create_plan(thread_id, {"v": 1}, db_url)
    repo.create_plan(thread_id, {"v": 2}, db_url)
    repo.create_plan(thread_id, {"v": 3}, db_url)
    versions = repo.list_plan_versions(thread_id, db_url)
    assert [p.version for p in versions] == [3, 2, 1]


def test_update_plan_status_atomic(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    assert repo.update_plan_status(plan.plan_id, "approved", db_url) is True
    refreshed = repo.get_latest_plan(thread_id, db_url)
    assert refreshed is not None
    assert refreshed.status == "approved"
    # Bogus plan_id → no row updated, returns False.
    assert repo.update_plan_status(uuid4(), "approved", db_url) is False


# ============================================================
# RESEARCH_STEPS
# ============================================================


def test_create_step_and_get_steps_ordinal_ordered(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    steps_repo.create_step(plan.plan_id, 2, "second", db_url)
    steps_repo.create_step(plan.plan_id, 1, "first", db_url)
    steps_repo.create_step(plan.plan_id, 3, "third", db_url)
    steps = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert [s.ordinal for s in steps] == [1, 2, 3]
    assert [s.description for s in steps] == ["first", "second", "third"]
    assert all(s.status == "pending" for s in steps)


def test_update_step_status_writes_timestamps_when_given(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    step = steps_repo.create_step(plan.plan_id, 1, "demo", db_url)
    started = datetime.now(UTC)
    assert steps_repo.update_step_status(
        step.step_id, "running", db_url, started_at=started
    )
    steps = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert steps[0].status == "running"
    assert steps[0].started_at is not None
    completed = datetime.now(UTC)
    assert steps_repo.update_step_status(
        step.step_id, "complete", db_url, completed_at=completed
    )
    steps = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert steps[0].status == "complete"
    assert steps[0].completed_at is not None


# ============================================================
# RESEARCH_FINDINGS
# ============================================================


def test_append_finding_all_jsonb_round_trips(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    step = steps_repo.create_step(plan.plan_id, 1, "fetch", db_url)
    rows = [{"branch": "Main", "balance": 1000.5}]
    mf_query = {"metric": "deposit_balance", "limit": 1}
    cited = [{"row_id": 42}]
    finding = steps_repo.append_finding(
        step.step_id,
        db_url,
        summary_text="Main has the highest balance.",
        structured_rows_json=rows,
        mf_query_json=mf_query,
        cited_artifacts=cited,
    )
    assert finding.summary_text == "Main has the highest balance."
    assert finding.structured_rows_json == rows
    assert finding.mf_query_json == mf_query
    assert finding.cited_artifacts == cited


def test_get_findings_for_plan_joins_across_steps(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    s1 = steps_repo.create_step(plan.plan_id, 1, "s1", db_url)
    s2 = steps_repo.create_step(plan.plan_id, 2, "s2", db_url)
    steps_repo.append_finding(s2.step_id, db_url, summary_text="b")
    steps_repo.append_finding(s1.step_id, db_url, summary_text="a")
    findings = steps_repo.get_findings_for_plan(plan.plan_id, db_url)
    # Ordered by step ordinal: a (s1) then b (s2).
    assert [f.summary_text for f in findings] == ["a", "b"]


# ============================================================
# RESEARCH_LEAD_NOTES
# ============================================================


def test_append_lead_note_auto_versions(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    n1 = repo.append_lead_note(plan.plan_id, "first thoughts", db_url)
    n2 = repo.append_lead_note(plan.plan_id, "more thoughts", db_url)
    n3 = repo.append_lead_note(plan.plan_id, "final thoughts", db_url)
    assert [n.version for n in (n1, n2, n3)] == [1, 2, 3]


def test_get_latest_lead_note(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    repo.append_lead_note(plan.plan_id, "v1", db_url)
    repo.append_lead_note(plan.plan_id, "v2", db_url)
    repo.append_lead_note(plan.plan_id, "v3", db_url)
    latest = repo.get_latest_lead_note(plan.plan_id, db_url)
    assert latest is not None
    assert latest.version == 3
    assert latest.body_md == "v3"


def test_get_latest_lead_note_none_for_unknown_plan() -> None:
    db_url = _db_url()
    assert repo.get_latest_lead_note(uuid4(), db_url) is None


def test_list_lead_notes_newest_first(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = repo.create_plan(thread_id, {}, db_url)
    for body in ("a", "b", "c"):
        repo.append_lead_note(plan.plan_id, body, db_url)
    notes = repo.list_lead_notes(plan.plan_id, db_url)
    assert [n.version for n in notes] == [3, 2, 1]
    assert [n.body_md for n in notes] == ["c", "b", "a"]
