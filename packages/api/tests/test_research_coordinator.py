"""Coordinator skeleton tests (HUG-205, F4).

Phase-1 behaviour: `route_turn` is a thin wrapper that emits the
`research.turn.routed` telemetry, bumps the shallow counter, and
delegates byte-identically to `stream_user_turn`. These tests pin
that contract so the L1 planner swap (HUG-208) doesn't accidentally
change the shallow path's wire output.

Live Postgres + a stub LLM, mirroring `test_threads_route.py`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.prometheus import research_turns_total
from api.repo import threads as threads_repo
from api.services.agent_runner import stream_user_turn
from api.services.research_agent import coordinator
from api.services.research_agent.coordinator import route_turn
from api.services.research_agent.planner import PlanDraft
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_DB_URL = os.environ.get("DATABASE_URL")


class _FinalAnswerLLM(BaseChatModel):
    """Deterministic stub: every invoke returns one final_answer
    tool call. Lets us drive the agent end-to-end without an LLM."""

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {"summary": "ok", "rows": [{"x": 1}]},
                    "id": "c1",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(  # type: ignore[override]
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FinalAnswerLLM:
        return self


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> UUID:
    """Seed a throwaway thread; teardown cascades-deletes any rows
    the agent wrote under it."""
    db_url = _db_url()
    sid = f"pytest-research-coordinator-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        cur.execute(
            "DELETE FROM threads WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        conn.commit()


@pytest.fixture
def stub_shallow_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the planner with a deterministic 'shallow' verdict so
    the coordinator-routing tests don't depend on a live LLM call.
    The planner itself is tested in `test_research_planner.py`."""

    def _stub(_user_question: str, _history: Any, _llm: Any) -> PlanDraft:
        return PlanDraft(
            route="shallow",
            reason="stub-shallow",
            plan=None,
            research_question_summary="stub",
        )

    monkeypatch.setattr(coordinator, "draft_plan", _stub)


async def _drain(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for event in stream:
        out.append(event)
    return out


def _wipe_thread_messages(db_url: str, thread_id: UUID) -> None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id = %s",
            (str(thread_id),),
        )
        conn.commit()


def test_route_turn_produces_same_events_as_stream_user_turn(
    thread_id: UUID, stub_shallow_planner: None
) -> None:
    """Golden trace: kinds of events emitted are identical when the
    coordinator and the underlying agent runner are called directly."""
    db_url = _db_url()
    llm = _FinalAnswerLLM()
    via_coordinator = asyncio.run(
        _drain(
            route_turn(
                thread_id=thread_id,
                user_content="hello via coordinator",
                db_url=db_url,
                llm=llm,
                history=[],
                request_id="rid-coordinator",
            )
        )
    )
    # Clean up the persisted rows from the first call so the second
    # call starts from the same DB state.
    _wipe_thread_messages(db_url, thread_id)
    via_direct = asyncio.run(
        _drain(
            stream_user_turn(
                thread_id=thread_id,
                user_content="hello direct",
                db_url=db_url,
                llm=llm,
                history=[],
                request_id="rid-direct",
            )
        )
    )
    # Same set of event types in the same order. The data payloads
    # legitimately differ (UUIDs, timestamps); only the SSE event-
    # type sequence is the invariant.
    assert [e["event"] for e in via_coordinator] == [
        e["event"] for e in via_direct
    ]
    assert "final" in {e["event"] for e in via_coordinator}


def test_route_turn_bumps_shallow_counter(
    thread_id: UUID, stub_shallow_planner: None
) -> None:
    before = research_turns_total.labels(route="shallow")._value.get()  # type: ignore[attr-defined]
    asyncio.run(
        _drain(
            route_turn(
                thread_id=thread_id,
                user_content="counter test",
                db_url=_db_url(),
                llm=_FinalAnswerLLM(),
                history=[],
            )
        )
    )
    after = research_turns_total.labels(route="shallow")._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_route_turn_emits_routed_event_once(
    thread_id: UUID,
    capsys: pytest.CaptureFixture[str],
    stub_shallow_planner: None,
) -> None:
    """`research.turn.routed` fires exactly once per call, with
    `route='shallow'` and the planner's reason. Structlog writes
    JSON to stdout, so we capture via `capsys`."""
    asyncio.run(
        _drain(
            route_turn(
                thread_id=thread_id,
                user_content="event check",
                db_url=_db_url(),
                llm=_FinalAnswerLLM(),
                history=[],
            )
        )
    )
    captured = capsys.readouterr().out
    routed_lines = [
        line for line in captured.splitlines()
        if '"event": "research.turn.routed"' in line
    ]
    assert len(routed_lines) == 1, (
        f"expected one research.turn.routed line; got {len(routed_lines)}"
    )
    assert '"route": "shallow"' in routed_lines[0]
    assert '"reason": "stub-shallow"' in routed_lines[0]
