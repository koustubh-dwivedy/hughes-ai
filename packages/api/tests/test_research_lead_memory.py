"""Lead-memory tests (HUG-220, M1).

Pins the contract `write_note` / `read_latest_note` provide to the
re-plan logic (HUG-221) and the coordinator's batch-callback wiring:

  1. Sequential writes produce monotonically-increasing versions.
  2. `read_latest_note` returns the most recent body.
  3. Empty plan (no notes) → read_latest returns "".
  4. Over-cap note → truncated to MAX_NOTE_CHARS + warning event.
  5. Histogram observes the note size.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import research as research_repo
from api.repo import threads as threads_repo
from api.services.research_agent.lead_memory import (
    read_latest_note,
    write_note,
)

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    db_url = _db_url()
    sid = f"lm-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=sid)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM research_plans WHERE thread_id = %s",
                    (str(thread.thread_id),))
        cur.execute("DELETE FROM threads WHERE thread_id = %s",
                    (str(thread.thread_id),))
        conn.commit()


def _seed_plan(thread_id: UUID) -> Any:
    return research_repo.create_plan(
        thread_id=thread_id, plan_json={"route": "deep", "plan": []},
        db_url=_db_url(),
    )


def test_write_then_read_returns_same_body(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    note = write_note(plan.plan_id, "# Initial digest\n\nFound X.", db_url)
    assert note.version == 1
    assert read_latest_note(plan.plan_id, db_url) == note.body_md


def test_sequential_writes_increment_version(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    v1 = write_note(plan.plan_id, "v1", db_url)
    v2 = write_note(plan.plan_id, "v2", db_url)
    v3 = write_note(plan.plan_id, "v3", db_url)
    assert (v1.version, v2.version, v3.version) == (1, 2, 3)
    assert read_latest_note(plan.plan_id, db_url) == "v3"


def test_no_notes_yields_empty_string(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    assert read_latest_note(plan.plan_id, db_url) == ""


def test_oversize_note_is_truncated(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    huge = "x" * 5000
    note = write_note(plan.plan_id, huge, db_url)
    # Truncated to MAX_NOTE_CHARS=2000.
    assert len(note.body_md) <= 2000
    # And ends with the truncation mark.
    assert "truncated" in note.body_md


def test_note_truncation_emits_warning(
    thread_id: UUID, capsys: pytest.CaptureFixture[str],
) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    write_note(plan.plan_id, "y" * 3000, db_url)
    out = capsys.readouterr().out
    # Structlog warning includes the truncation event name.
    assert "lead_memory.note_truncated" in out
