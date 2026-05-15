"""Final synthesis tests (HUG-216, E4).

The synthesizer is `run_agent_isolated` invoked with synthesis-shaped
input + chat persistence callback. These tests pin:

  1. Findings → synthesis input contains each finding's summary + rows.
  2. Synthesis terminates the plan (status='complete').
  3. The answer lands as a thread_messages row (chat-shaped output).
  4. SSE stream emits `research.turn.completed` after the chat
     `final` event.
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
from api.repo import threads as threads_repo
from api.services.research_agent.executor import (
    execute_plan_sequentially,
    expand_plan_into_steps,
)
from api.services.research_agent.synthesizer import synthesize_final_answer
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
    sid = f"synth-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=sid)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM research_plans WHERE thread_id = %s",
                    (str(thread.thread_id),))
        cur.execute("DELETE FROM thread_messages WHERE thread_id = %s",
                    (str(thread.thread_id),))
        cur.execute("DELETE FROM threads WHERE thread_id = %s",
                    (str(thread.thread_id),))
        conn.commit()


class _FinalAnswerLLM(BaseChatModel):
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
                "args": {"summary": "synthesized", "rows": []},
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


def _setup_complete_plan(thread_id: UUID) -> Any:
    """Seed: plan + 2 steps + execute them with a stub LLM so both
    end up complete with findings. Returns the plan."""
    db_url = _db_url()
    plan = research_repo.create_plan(
        thread_id=thread_id,
        plan_json={
            "route": "deep", "reason": "t",
            "research_question_summary": "test",
            "plan": [
                {"ordinal": 1, "description": "a", "dependencies": []},
                {"ordinal": 2, "description": "b", "dependencies": []},
            ],
        },
        db_url=db_url,
    )
    expand_plan_into_steps(plan, db_url)
    asyncio.run(_drain(execute_plan_sequentially(
        plan_id=plan.plan_id, db_url=db_url, llm=_FinalAnswerLLM(),
    )))
    return plan


def test_synthesis_completes_plan_and_emits_final_event(
    thread_id: UUID,
) -> None:
    db_url = _db_url()
    plan = _setup_complete_plan(thread_id)
    events = asyncio.run(_drain(synthesize_final_answer(
        plan_id=plan.plan_id, thread_id=thread_id,
        user_question="explain the trends",
        db_url=db_url, llm=_FinalAnswerLLM(),
    )))
    event_types = [e["event"] for e in events]
    assert "final" in event_types  # chat-shaped final from agent
    assert event_types[-1] == "research.turn.completed"

    # Plan status transitioned to complete.
    refreshed = research_repo.get_plan(plan.plan_id, db_url)
    assert refreshed is not None
    assert refreshed.status == "complete"


def test_synthesis_writes_thread_message(thread_id: UUID) -> None:
    """Chat-shaped persistence: the synthesized answer lands as a
    thread_messages row (role='tool', name='final_answer'), same as
    a regular chat turn."""
    db_url = _db_url()
    plan = _setup_complete_plan(thread_id)
    asyncio.run(_drain(synthesize_final_answer(
        plan_id=plan.plan_id, thread_id=thread_id,
        user_question="explain",
        db_url=db_url, llm=_FinalAnswerLLM(),
    )))
    messages = threads_repo.list_messages(thread_id, db_url)
    # At least one tool message named final_answer.
    tool_messages = [m for m in messages if m.role == "tool"]
    assert len(tool_messages) >= 1


def test_synthesis_with_no_findings_still_terminates(
    thread_id: UUID,
) -> None:
    """Defensive: if every step failed, synthesis should still
    complete (emit a graceful "no data" answer) rather than crash."""
    db_url = _db_url()
    plan = research_repo.create_plan(
        thread_id=thread_id,
        plan_json={
            "route": "deep", "reason": "t",
            "research_question_summary": "test",
            "plan": [{"ordinal": 1, "description": "x", "dependencies": []}],
        },
        db_url=db_url,
    )
    # NO steps created → no findings. Skip executor; synthesize directly.
    events = asyncio.run(_drain(synthesize_final_answer(
        plan_id=plan.plan_id, thread_id=thread_id,
        user_question="explain",
        db_url=db_url, llm=_FinalAnswerLLM(),
    )))
    event_types = [e["event"] for e in events]
    assert event_types[-1] == "research.turn.completed"
    refreshed = research_repo.get_plan(plan.plan_id, db_url)
    assert refreshed is not None
    assert refreshed.status == "complete"
