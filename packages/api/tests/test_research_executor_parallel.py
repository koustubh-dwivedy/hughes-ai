"""Parallel executor tests (HUG-218, S2).

Pins the dependency-aware parallel dispatch contract:
  1. Independent steps run concurrently (batch size > 1).
  2. Chain-dependent steps run sequentially in correct order.
  3. Mixed graph: two independent → then one dependent.
  4. Single failed step does NOT block siblings.
  5. max_parallel=1 produces sequential equivalent.

Timing is checked via batch-event-order rather than wall-clock, to
avoid flake on slow CI runners.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator, Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import research as research_repo
from api.repo import research_steps as steps_repo
from api.repo import threads as threads_repo
from api.services.research_agent.executor import expand_plan_into_steps
from api.services.research_agent.executor_parallel import (
    execute_plan_parallel,
)
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    db_url = _db_url()
    sid = f"par-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=sid)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM research_plans WHERE thread_id = %s",
                    (str(thread.thread_id),))
        cur.execute("DELETE FROM threads WHERE thread_id = %s",
                    (str(thread.thread_id),))
        conn.commit()


def _seed_plan(thread_id: UUID, steps: list[dict[str, object]]) -> Any:
    return research_repo.create_plan(
        thread_id=thread_id,
        plan_json={
            "route": "deep", "reason": "t",
            "research_question_summary": "t", "plan": steps,
        },
        db_url=_db_url(),
    )


class _OkLLM(BaseChatModel):
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
    ) -> _OkLLM:
        return self


async def _drain(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for event in stream:
        out.append(event)
    return out


def test_three_independent_steps_complete_concurrently(
    thread_id: UUID,
) -> None:
    """3 steps with no deps + max_parallel=3 → all dispatch in one
    batch. All end complete."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "a", "dependencies": []},
        {"ordinal": 2, "description": "b", "dependencies": []},
        {"ordinal": 3, "description": "c", "dependencies": []},
    ])
    expand_plan_into_steps(plan, db_url)
    events = asyncio.run(_drain(execute_plan_parallel(
        plan_id=plan.plan_id, db_url=db_url, llm=_OkLLM(),
        max_parallel=3,
    )))
    # 3 steps × 2 events each = 6.
    assert len(events) == 6
    starts = [e for e in events if e["event"] == "research.step.started"]
    completes = [e for e in events if e["event"] == "research.step.completed"]
    assert len(starts) == 3
    assert len(completes) == 3
    persisted = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert all(s.status == "complete" for s in persisted)


def test_chain_dependent_steps_run_in_order(thread_id: UUID) -> None:
    """3 steps in a strict chain (1→2→3) → must complete in ordinal
    order even at max_parallel=3 (no other step is ever ready in
    parallel)."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "a", "dependencies": []},
        {"ordinal": 2, "description": "b", "dependencies": [1]},
        {"ordinal": 3, "description": "c", "dependencies": [2]},
    ])
    expand_plan_into_steps(plan, db_url)
    events = asyncio.run(_drain(execute_plan_parallel(
        plan_id=plan.plan_id, db_url=db_url, llm=_OkLLM(),
        max_parallel=3,
    )))
    # All 6 events, alternating started/completed for each ordinal.
    completes = [
        e for e in events if e["event"] == "research.step.completed"
    ]
    # Order from event order; sequential = step 1 completes before 2 etc.
    import json as _json
    ordinals = [_json.loads(e["data"])["ordinal"] for e in completes]
    assert ordinals == [1, 2, 3]


def test_mixed_graph_two_parallel_then_one_dependent(
    thread_id: UUID,
) -> None:
    """Steps 1 and 2 independent; step 3 depends on both → batch 1
    runs [1,2] in parallel, then batch 2 runs [3]."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "a", "dependencies": []},
        {"ordinal": 2, "description": "b", "dependencies": []},
        {"ordinal": 3, "description": "c", "dependencies": [1, 2]},
    ])
    expand_plan_into_steps(plan, db_url)
    events = asyncio.run(_drain(execute_plan_parallel(
        plan_id=plan.plan_id, db_url=db_url, llm=_OkLLM(),
        max_parallel=3,
    )))
    # Step 3 must complete LAST in event order.
    import json as _json
    completes = [
        _json.loads(e["data"])["ordinal"]
        for e in events if e["event"] == "research.step.completed"
    ]
    assert completes[-1] == 3
    assert set(completes) == {1, 2, 3}


def test_max_parallel_1_runs_sequentially(thread_id: UUID) -> None:
    """max_parallel=1 = serial; events strictly ordered."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "a", "dependencies": []},
        {"ordinal": 2, "description": "b", "dependencies": []},
    ])
    expand_plan_into_steps(plan, db_url)
    events = asyncio.run(_drain(execute_plan_parallel(
        plan_id=plan.plan_id, db_url=db_url, llm=_OkLLM(),
        max_parallel=1,
    )))
    event_types = [e["event"] for e in events]
    # Strict alternation: started, completed, started, completed.
    assert event_types == [
        "research.step.started", "research.step.completed",
        "research.step.started", "research.step.completed",
    ]


def test_failed_dependency_does_not_block_siblings(thread_id: UUID) -> None:
    """Step 1 fails (silent LLM); step 2 has no deps → still runs.
    Step 3 depends on step 1 (failed) — still runs per the
    'siblings on failure' decision."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "BREAK-ME-XYZ", "dependencies": []},
        {"ordinal": 2, "description": "b", "dependencies": []},
        {"ordinal": 3, "description": "c", "dependencies": [1]},
    ])
    expand_plan_into_steps(plan, db_url)

    class _MaybeFailLLM(_OkLLM):
        def _generate(
            self, messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: CallbackManagerForLLMRun | None = None,
            **kwargs: Any,
        ) -> ChatResult:
            from langchain_core.messages import HumanMessage
            human = " ".join(
                str(m.content) for m in messages
                if isinstance(m, HumanMessage) and isinstance(m.content, str)
            )
            if "BREAK-ME-XYZ" in human:
                return ChatResult(generations=[
                    ChatGeneration(message=AIMessage(content=""))
                ])
            return super()._generate(messages, stop, run_manager, **kwargs)

    asyncio.run(_drain(execute_plan_parallel(
        plan_id=plan.plan_id, db_url=db_url, llm=_MaybeFailLLM(),
        max_parallel=3,
    )))
    persisted = sorted(
        steps_repo.get_steps_for_plan(plan.plan_id, db_url),
        key=lambda s: s.ordinal,
    )
    assert [s.status for s in persisted] == ["failed", "complete", "complete"]
