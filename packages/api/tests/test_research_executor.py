"""Executor tests (HUG-213 + HUG-214).

`expand_plan_into_steps` (HUG-213, E1) — pending row creation.
`execute_plan_sequentially` (HUG-214, E2) — ordered worker dispatch.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator, Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.prometheus import research_steps_total
from api.repo import research as research_repo
from api.repo import research_steps as steps_repo
from api.repo import threads as threads_repo
from api.services.research_agent.executor import (
    execute_plan_sequentially,
    expand_plan_into_steps,
)
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

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


# ---- HUG-214 (E2): sequential execution -----------------------


class _FinalAnswerLLM(BaseChatModel):
    """Stub: every invoke returns one final_answer tool call."""

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self, messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content="",
            tool_calls=[{
                "name": "final_answer",
                "args": {"summary": "ok", "rows": [{"x": 1}]},
                "id": "c1",
            }],
        ))])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FinalAnswerLLM:
        return self


async def _drain(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for event in stream:
        out.append(event)
    return out


def test_three_step_plan_executes_in_ordinal_order(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "A", "dependencies": []},
        {"ordinal": 2, "description": "B", "dependencies": [1]},
        {"ordinal": 3, "description": "C", "dependencies": [2]},
    ])
    expand_plan_into_steps(plan, db_url)
    events = asyncio.run(_drain(execute_plan_sequentially(
        plan_id=plan.plan_id, db_url=db_url, llm=_FinalAnswerLLM(),
    )))
    # 3 steps × 2 events (started + completed) = 6.
    assert len(events) == 6
    event_types = [e["event"] for e in events]
    # Alternating started/completed pairs.
    assert event_types == [
        "research.step.started", "research.step.completed",
        "research.step.started", "research.step.completed",
        "research.step.started", "research.step.completed",
    ]
    persisted = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert all(s.status == "complete" for s in persisted)


# HUG-215 (E3) finding-persistence invariants moved to
# test_research_findings.py to keep this file under the 300-line cap.


def test_step_failure_does_not_abort_loop(thread_id: UUID) -> None:
    """One worker raises → that step marked failed, siblings still run."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "step A", "dependencies": []},
        {"ordinal": 2, "description": "BREAK-ME-XYZ", "dependencies": []},
        {"ordinal": 3, "description": "step C", "dependencies": []},
    ])
    expand_plan_into_steps(plan, db_url)

    class _BrokenLLM(_FinalAnswerLLM):
        """For the 'BREAK-ME-XYZ' step, return empty content with NO
        tool calls → agent exits without firing final_answer → worker
        returns None → executor marks step failed.

        Magic sentinel ('BREAK-ME-XYZ') is chosen to be absent from
        the agent's system prompt so it ONLY matches step 2's user
        input (not 'FAIL', which the system prompt also contains)."""
        def _generate(
            self, messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: CallbackManagerForLLMRun | None = None,
            **kwargs: Any,
        ) -> ChatResult:
            # Inspect only the HumanMessage(s) — the worker's user
            # input. Avoids accidental matches in the system prompt.
            from langchain_core.messages import HumanMessage
            human_content = " ".join(
                str(m.content) for m in messages
                if isinstance(m, HumanMessage) and isinstance(m.content, str)
            )
            if "BREAK-ME-XYZ" in human_content:
                return ChatResult(generations=[
                    ChatGeneration(message=AIMessage(content=""))
                ])
            return super()._generate(messages, stop, run_manager, **kwargs)

    events = asyncio.run(_drain(execute_plan_sequentially(
        plan_id=plan.plan_id, db_url=db_url, llm=_BrokenLLM(),
    )))
    event_types = [e["event"] for e in events]
    # Step 1: started + completed; step 2: started + failed;
    # step 3: started + completed.
    assert event_types.count("research.step.started") == 3
    assert event_types.count("research.step.completed") == 2
    assert event_types.count("research.step.failed") == 1
    persisted = sorted(
        steps_repo.get_steps_for_plan(plan.plan_id, db_url),
        key=lambda s: s.ordinal,
    )
    assert [s.status for s in persisted] == ["complete", "failed", "complete"]
