"""HUG-266 — turn_state repo CRUD + lifecycle tests."""

from __future__ import annotations

import os
import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import turn_state as repo

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")
_MIGRATION = (
    Path(__file__).resolve().parents[3] / "migrations" / "018_turn_state.sql"
)


def _apply_migration() -> None:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    sql = _MIGRATION.read_text()
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(sql)


def _seed_thread() -> UUID:
    """Insert a minimal thread row so turn_state's FK is satisfied."""
    assert _DB_URL is not None
    tid = uuid4()
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id)"
            " VALUES (%s, %s, %s)",
            (str(tid), str(uuid4()), str(uuid4())),
        )
    return tid


def test_create_running_returns_running_row() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn_id = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    obj = repo.get_by_id(turn_id, _DB_URL)  # type: ignore[arg-type]
    assert obj is not None
    assert obj.status == "running"
    assert obj.thread_id == tid
    assert obj.completed_at is None
    assert obj.error_text is None
    assert obj.last_seq_no is None


def test_mark_complete_flips_status_and_persists_last_seq() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn_id = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    repo.mark_complete(turn_id, last_seq_no=42, db_url=_DB_URL)  # type: ignore[arg-type]
    obj = repo.get_by_id(turn_id, _DB_URL)  # type: ignore[arg-type]
    assert obj is not None
    assert obj.status == "complete"
    assert obj.last_seq_no == 42
    assert obj.completed_at is not None


def test_mark_failed_persists_error_text() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn_id = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    repo.mark_failed(turn_id, "synthetic crash", db_url=_DB_URL)  # type: ignore[arg-type]
    obj = repo.get_by_id(turn_id, _DB_URL)  # type: ignore[arg-type]
    assert obj is not None
    assert obj.status == "failed"
    assert obj.error_text == "synthetic crash"


def test_mark_complete_is_idempotent_against_already_completed() -> None:
    """mark_complete updates WHERE status='running'; a second call on
    an already-complete turn must be a no-op (not corrupt the row)."""
    _apply_migration()
    tid = _seed_thread()
    turn_id = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    repo.mark_complete(turn_id, last_seq_no=10, db_url=_DB_URL)  # type: ignore[arg-type]
    first = repo.get_by_id(turn_id, _DB_URL)  # type: ignore[arg-type]
    assert first is not None
    first_completed_at = first.completed_at
    # Second call should not change last_seq_no or completed_at.
    repo.mark_complete(turn_id, last_seq_no=999, db_url=_DB_URL)  # type: ignore[arg-type]
    second = repo.get_by_id(turn_id, _DB_URL)  # type: ignore[arg-type]
    assert second is not None
    assert second.last_seq_no == 10
    assert second.completed_at == first_completed_at


def test_get_running_for_thread_returns_only_running() -> None:
    _apply_migration()
    tid = _seed_thread()
    # No running turn yet → None.
    assert repo.get_running_for_thread(tid, _DB_URL) is None  # type: ignore[arg-type]
    # Create one → returned.
    turn_id = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    obj = repo.get_running_for_thread(tid, _DB_URL)  # type: ignore[arg-type]
    assert obj is not None and obj.turn_id == turn_id
    # Complete it → None again.
    repo.mark_complete(turn_id, 5, _DB_URL)  # type: ignore[arg-type]
    assert repo.get_running_for_thread(tid, _DB_URL) is None  # type: ignore[arg-type]


def test_cleanup_stale_only_affects_old_running_rows() -> None:
    _apply_migration()
    tid_old = _seed_thread()
    tid_new = _seed_thread()
    tid_done = _seed_thread()

    # Old running row (will be cleaned).
    old_turn = repo.create_running(tid_old, _DB_URL)  # type: ignore[arg-type]
    # Backdate it so started_at is older than the threshold.
    assert _DB_URL is not None
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE turn_state SET started_at = NOW() - INTERVAL '20 minutes'"
            " WHERE turn_id = %s",
            (str(old_turn),),
        )

    # Fresh running row (must NOT be touched).
    fresh_turn = repo.create_running(tid_new, _DB_URL)  # type: ignore[arg-type]

    # Already-complete row (must NOT be touched even if old).
    done_turn = repo.create_running(tid_done, _DB_URL)  # type: ignore[arg-type]
    repo.mark_complete(done_turn, 3, _DB_URL)  # type: ignore[arg-type]
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE turn_state SET started_at = NOW() - INTERVAL '30 minutes'"
            " WHERE turn_id = %s",
            (str(done_turn),),
        )

    cleaned = repo.cleanup_stale(_DB_URL, timedelta(minutes=10))  # type: ignore[arg-type]
    assert cleaned == 1

    assert repo.get_by_id(old_turn, _DB_URL).status == "failed"  # type: ignore[union-attr,arg-type]
    assert "orphaned" in (repo.get_by_id(old_turn, _DB_URL).error_text or "")  # type: ignore[union-attr,arg-type]
    assert repo.get_by_id(fresh_turn, _DB_URL).status == "running"  # type: ignore[union-attr,arg-type]
    assert repo.get_by_id(done_turn, _DB_URL).status == "complete"  # type: ignore[union-attr,arg-type]


def test_create_running_writes_distinct_ids_under_concurrency() -> None:
    """Two consecutive create_running calls return different UUIDs even
    when issued in quick succession on the same thread."""
    _apply_migration()
    tid = _seed_thread()
    a = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    time.sleep(0.001)
    b = repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    assert a != b
