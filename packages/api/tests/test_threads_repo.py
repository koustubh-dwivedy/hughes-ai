"""Round-trip tests for the threads + thread_messages repo (HUG-175).

These exercise real Postgres so they live in the integration tier per the
existing CI pattern. The integration job applies all migrations and seeds
the DB; we only need to clean up our own rows after each test.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from api.repo import threads as repo


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set; threads-repo tests need Postgres")
    return url


@pytest.fixture
def session_id() -> str:
    """Each test gets its own session_id so concurrent runs don't collide."""
    return f"pytest-{uuid4().hex[:12]}"


def test_create_thread_round_trip(session_id: str) -> None:
    db_url = _db_url()
    created = repo.create_thread(session_id, db_url, title="Round-trip thread")
    assert created.session_id == session_id
    assert created.title == "Round-trip thread"
    assert created.slots == {}

    fetched = repo.get_thread(created.thread_id, db_url)
    assert fetched is not None
    assert fetched.thread_id == created.thread_id
    assert fetched.session_id == session_id
    assert fetched.title == "Round-trip thread"


def test_get_unknown_thread_returns_none() -> None:
    assert repo.get_thread(uuid4(), _db_url()) is None


def test_list_threads_for_session_orders_by_last_active(session_id: str) -> None:
    db_url = _db_url()
    t1 = repo.create_thread(session_id, db_url, title="first")
    t2 = repo.create_thread(session_id, db_url, title="second")
    repo.append_message(t1.thread_id, "user", db_url, content="ping")

    listed = repo.list_threads_for_session(session_id, db_url)
    ids = [t.thread_id for t in listed]
    # t1 was bumped to most-recent active by the append; t2 is older now
    assert ids[0] == t1.thread_id
    assert ids[1] == t2.thread_id


def test_append_message_round_trip_with_jsonb(session_id: str) -> None:
    db_url = _db_url()
    thread = repo.create_thread(session_id, db_url)
    user_msg = repo.append_message(
        thread.thread_id, "user", db_url, content="What's our delinquency rate?"
    )
    assistant_msg = repo.append_message(
        thread.thread_id,
        "assistant",
        db_url,
        parent_message_id=user_msg.message_id,
        content="0.45%",
        tool_calls=[{"name": "mf_query", "args": {"metric": "delinquency_rate"}}],
        tool_results=[{"name": "mf_query", "result": [{"value": 0.0045}]}],
        openui_dsl="<KpiTile value='0.45%' label='Delinquency Rate'/>",
        mf_query={"metric": "delinquency_rate", "time_grain": "month"},
        rows=[{"value": 0.0045}],
    )

    assert assistant_msg.parent_message_id == user_msg.message_id
    assert assistant_msg.tool_calls is not None
    assert assistant_msg.tool_calls[0]["name"] == "mf_query"
    assert assistant_msg.openui_dsl is not None
    assert "KpiTile" in assistant_msg.openui_dsl
    assert assistant_msg.mf_query == {
        "metric": "delinquency_rate",
        "time_grain": "month",
    }
    assert assistant_msg.rows == [{"value": 0.0045}]


def test_list_messages_chronological(session_id: str) -> None:
    db_url = _db_url()
    thread = repo.create_thread(session_id, db_url)
    a = repo.append_message(thread.thread_id, "user", db_url, content="a")
    b = repo.append_message(thread.thread_id, "assistant", db_url, content="b")
    c = repo.append_message(thread.thread_id, "user", db_url, content="c")

    messages = repo.list_messages(thread.thread_id, db_url)
    expected_ids = [a.message_id, b.message_id, c.message_id]
    assert [m.message_id for m in messages] == expected_ids
    assert [m.content for m in messages] == ["a", "b", "c"]


def test_latest_n_messages_returns_oldest_first(session_id: str) -> None:
    db_url = _db_url()
    thread = repo.create_thread(session_id, db_url)
    msgs = [
        repo.append_message(thread.thread_id, "user", db_url, content=str(i))
        for i in range(5)
    ]
    last_three = repo.latest_n_messages(thread.thread_id, 3, db_url)
    assert [m.message_id for m in last_three] == [
        msgs[2].message_id,
        msgs[3].message_id,
        msgs[4].message_id,
    ]


def test_fk_violation_on_unknown_thread() -> None:
    """Cannot append a message to a non-existent thread."""
    import psycopg.errors

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        repo.append_message(uuid4(), "user", _db_url(), content="orphan")
