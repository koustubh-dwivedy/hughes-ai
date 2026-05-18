"""HUG-266 — tail_turn DB-polling SSE producer tests.

Exercises live local DB so migration + repo + tail contract roll up
into one validation. No pytest-asyncio dep — tests use `asyncio.run`
directly to drive the async generator.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import threads as threads_repo
from api.repo import turn_state as turn_state_repo
from api.services.tail_turn import tail_turn
from api.services.turn_context import bind_turn_context, reset_turn_context

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
    assert _DB_URL is not None
    tid = uuid4()
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (thread_id, session_id, user_id)"
            " VALUES (%s, %s, %s)",
            (str(tid), str(uuid4()), str(uuid4())),
        )
    return tid


def _persist_assistant_prose(thread_id: UUID, turn_id: UUID, content: str) -> None:
    assert _DB_URL is not None
    token = bind_turn_context(turn_id)
    try:
        threads_repo.append_message(
            thread_id=thread_id,
            role="assistant",
            db_url=_DB_URL,
            content=content,
            turn_id=turn_id,
        )
    finally:
        reset_turn_context(token)


def _persist_assistant_tool_call(thread_id: UUID, turn_id: UUID, tool: str) -> None:
    assert _DB_URL is not None
    threads_repo.append_message(
        thread_id=thread_id,
        role="assistant",
        db_url=_DB_URL,
        content="",
        tool_calls=[{"name": tool, "args": {}, "id": "call_1"}],
        turn_id=turn_id,
    )


def _persist_final_answer_tool(thread_id: UUID, turn_id: UUID, summary: str) -> None:
    assert _DB_URL is not None
    threads_repo.append_message(
        thread_id=thread_id,
        role="tool",
        db_url=_DB_URL,
        content=json.dumps({"summary": summary, "rows": [], "mf_query": {"x": 1}}),
        tool_results=[{"call_id": "call_1", "result": "ok"}],
        mf_query={"x": 1},
        rows=[],
        turn_id=turn_id,
    )


async def _drain(gen: Any, limit_sec: float = 5.0) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        async with asyncio.timeout(limit_sec):
            async for ev in gen:
                events.append(ev)
    except TimeoutError:
        pass
    return events


def test_tail_emits_stream_start_first() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn = turn_state_repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    turn_state_repo.mark_complete(turn, 0, _DB_URL)  # type: ignore[arg-type]
    events = asyncio.run(
        _drain(
            tail_turn(thread_id=tid, turn_id=turn, from_seq=0, db_url=_DB_URL),  # type: ignore[arg-type]
            limit_sec=2.0,
        )
    )
    assert events[0]["event"] == "stream.start"


def test_tail_emits_thinking_step_final_for_terminal_prose() -> None:
    """HUG-265 contract: a single assistant prose row (no tool_calls)
    produces thinking + step + final."""
    _apply_migration()
    tid = _seed_thread()
    turn = turn_state_repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    _persist_assistant_prose(tid, turn, "Hello! How can I help?")
    turn_state_repo.mark_complete(turn, 999, _DB_URL)  # type: ignore[arg-type]
    events = asyncio.run(
        _drain(
            tail_turn(thread_id=tid, turn_id=turn, from_seq=0, db_url=_DB_URL),  # type: ignore[arg-type]
            limit_sec=3.0,
        )
    )
    names = [e["event"] for e in events]
    assert "stream.start" in names
    assert "thinking" in names
    assert "step" in names
    assert "final" in names
    final = next(e for e in events if e["event"] == "final")
    data = json.loads(final["data"])
    assert data["message"]["content"] == "Hello! How can I help?"
    assert data["message"]["role"] == "assistant"


def test_tail_emits_final_for_final_answer_tool_message() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn = turn_state_repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    _persist_assistant_tool_call(tid, turn, "list_metrics")
    _persist_final_answer_tool(tid, turn, "We have 24 metrics.")
    turn_state_repo.mark_complete(turn, 999, _DB_URL)  # type: ignore[arg-type]
    events = asyncio.run(
        _drain(
            tail_turn(thread_id=tid, turn_id=turn, from_seq=0, db_url=_DB_URL),  # type: ignore[arg-type]
            limit_sec=3.0,
        )
    )
    finals = [e for e in events if e["event"] == "final"]
    assert len(finals) == 1
    data = json.loads(finals[0]["data"])
    assert data["message"]["role"] == "tool"
    assert data["message"]["mf_query"] == {"x": 1}


def test_tail_skips_rows_below_cursor() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn = turn_state_repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    _persist_assistant_prose(tid, turn, "first")
    assert _DB_URL is not None
    with psycopg.connect(_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(seq_no) FROM thread_messages WHERE turn_id=%s",
            (str(turn),),
        )
        cursor_after_first = cur.fetchone()[0]  # type: ignore[index]
    _persist_assistant_prose(tid, turn, "second")
    turn_state_repo.mark_complete(turn, 999, _DB_URL)  # type: ignore[arg-type]
    events = asyncio.run(
        _drain(
            tail_turn(
                thread_id=tid,
                turn_id=turn,
                from_seq=cursor_after_first,
                db_url=_DB_URL,  # type: ignore[arg-type]
            ),
            limit_sec=3.0,
        )
    )
    finals = [
        json.loads(e["data"])["message"]["content"]
        for e in events
        if e["event"] == "final"
    ]
    assert "second" in finals
    assert "first" not in finals


def test_tail_exits_when_status_flips_to_failed() -> None:
    _apply_migration()
    tid = _seed_thread()
    turn = turn_state_repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]
    turn_state_repo.mark_failed(turn, "synthetic", _DB_URL)  # type: ignore[arg-type]
    events = asyncio.run(
        _drain(
            tail_turn(thread_id=tid, turn_id=turn, from_seq=0, db_url=_DB_URL),  # type: ignore[arg-type]
            limit_sec=3.0,
        )
    )
    assert events[0]["event"] == "stream.start"


def test_tail_drains_row_written_just_before_status_flip() -> None:
    """The 'one final pass after status flip' guard catches late rows."""
    _apply_migration()
    tid = _seed_thread()
    turn = turn_state_repo.create_running(tid, _DB_URL)  # type: ignore[arg-type]

    async def _scenario() -> list[dict[str, Any]]:
        tail_task = asyncio.create_task(
            _drain(
                tail_turn(
                    thread_id=tid,
                    turn_id=turn,
                    from_seq=0,
                    db_url=_DB_URL,  # type: ignore[arg-type]
                ),
                limit_sec=5.0,
            )
        )
        await asyncio.sleep(0.3)
        turn_state_repo.mark_complete(turn, 999, _DB_URL)  # type: ignore[arg-type]
        _persist_assistant_prose(tid, turn, "late row written after flip")
        return await tail_task

    events = asyncio.run(_scenario())
    finals = [
        json.loads(e["data"])["message"]["content"]
        for e in events
        if e["event"] == "final"
    ]
    assert "late row written after flip" in finals
