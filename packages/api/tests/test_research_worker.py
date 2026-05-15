"""Worker wrapper tests (HUG-217, S1).

The worker is `run_agent_isolated` invoked with worker-shaped
defaults. Tests pin the four behaviours that distinguish it from
the chat path:

  1. Worker invocation produces one `research_findings` row per
     final_answer.
  2. Zero `thread_messages` rows written during worker execution
     (no chat-side persistence leaks through).
  3. Worker tagged with `research.subagent.spawned` /
     `research.subagent.completed` events.
  4. Worker honours its own (tighter) `max_steps` cap.

Mocks live LLM via the `_FinalAnswerLLM` stub pattern used elsewhere
in the suite.
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
from api.services.research_agent.worker import run_step_as_worker
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


class _FinalAnswerLLM(BaseChatModel):
    """One-shot stub: every invoke returns a single `final_answer`
    tool call with a known payload so we can assert finding fields."""

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
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content="",
            tool_calls=[{
                "name": "final_answer",
                "args": {
                    "summary": "worker result",
                    "rows": [{"k": 1}, {"k": 2}],
                },
                "id": "c1",
            }],
        ))])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FinalAnswerLLM:
        return self


@pytest.fixture
def thread_id() -> Iterator[UUID]:
    db_url = _db_url()
    sid = f"worker-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=sid)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM research_plans WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        cur.execute(
            "DELETE FROM threads WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        conn.commit()


def _seed_plan_with_one_step(thread_id: UUID) -> Any:
    db_url = _db_url()
    plan = research_repo.create_plan(
        thread_id=thread_id,
        plan_json={
            "route": "deep",
            "plan": [{"ordinal": 1, "description": "x", "dependencies": []}],
        },
        db_url=db_url,
    )
    step = steps_repo.create_step(
        plan_id=plan.plan_id, ordinal=1, description="test step",
        db_url=db_url,
    )
    return step


def _count_thread_messages(thread_id: UUID) -> int:
    db_url = _db_url()
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM thread_messages WHERE thread_id = %s",
            (str(thread_id),),
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0


def test_worker_persists_one_finding_per_final_answer(thread_id: UUID) -> None:
    db_url = _db_url()
    step = _seed_plan_with_one_step(thread_id)
    finding = asyncio.run(
        run_step_as_worker(
            step=step,
            plan_context="",
            db_url=db_url,
            llm=_FinalAnswerLLM(),
            request_id="rid-worker",
        )
    )
    assert finding is not None
    assert finding.step_id == step.step_id
    assert finding.summary_text == "worker result"
    assert finding.structured_rows_json == [{"k": 1}, {"k": 2}]
    persisted = steps_repo.get_findings_for_step(step.step_id, db_url)
    assert len(persisted) == 1


def test_worker_writes_no_thread_messages(thread_id: UUID) -> None:
    """The chat-path persistence callback writes to thread_messages.
    The worker callback must NOT — confirming policy isolation."""
    db_url = _db_url()
    step = _seed_plan_with_one_step(thread_id)
    before = _count_thread_messages(thread_id)
    asyncio.run(
        run_step_as_worker(
            step=step,
            plan_context="",
            db_url=db_url,
            llm=_FinalAnswerLLM(),
        )
    )
    after = _count_thread_messages(thread_id)
    assert after == before, (
        f"worker leaked into thread_messages: {after - before} rows"
    )


def test_worker_emits_subagent_events(
    thread_id: UUID, capsys: pytest.CaptureFixture[str]
) -> None:
    db_url = _db_url()
    step = _seed_plan_with_one_step(thread_id)
    asyncio.run(
        run_step_as_worker(
            step=step, plan_context="",
            db_url=db_url, llm=_FinalAnswerLLM(),
        )
    )
    out = capsys.readouterr().out
    assert '"event": "research.subagent.spawned"' in out
    assert '"event": "research.subagent.completed"' in out
    assert '"event": "research.finding.persisted"' in out


def test_worker_returns_none_when_max_steps_too_low(thread_id: UUID) -> None:
    """With `max_steps=1`, the cap fires after the LLM proposes the
    final_answer but BEFORE the ToolMessage is processed (cap counts
    LLM calls, not graph nodes). The worker returns None to signal
    'step did not produce a finding'; the caller (E2 sequential
    executor) marks the step failed."""
    db_url = _db_url()
    step = _seed_plan_with_one_step(thread_id)
    finding = asyncio.run(
        run_step_as_worker(
            step=step, plan_context="some context",
            db_url=db_url, llm=_FinalAnswerLLM(),
            max_steps=1,
        )
    )
    assert finding is None
    persisted = steps_repo.get_findings_for_step(step.step_id, db_url)
    assert persisted == []


def test_worker_plan_context_flows_into_user_input(thread_id: UUID) -> None:
    """A non-empty `plan_context` should appear in the message the
    LLM sees. Use a spy LLM that records its inputs."""
    db_url = _db_url()
    step = _seed_plan_with_one_step(thread_id)
    seen: list[str] = []

    class _SpyLLM(_FinalAnswerLLM):
        def _generate(
            self, messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: CallbackManagerForLLMRun | None = None,
            **kwargs: Any,
        ) -> ChatResult:
            for m in messages:
                if isinstance(m.content, str):
                    seen.append(m.content)
            return super()._generate(messages, stop, run_manager, **kwargs)

    asyncio.run(
        run_step_as_worker(
            step=step, plan_context="UPSTREAM-NOTE-XYZ",
            db_url=db_url, llm=_SpyLLM(),
        )
    )
    assert any("UPSTREAM-NOTE-XYZ" in s for s in seen)
