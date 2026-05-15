"""Finding persistence invariants (HUG-215, E3).

Persistence happens inside the worker's process_message callback
(HUG-217 worker_process_message.py). These tests pin the invariants
the executor relies on:

  1. A `complete` step has exactly one `research_findings` row
     whose JSONB columns round-trip from the final_answer payload.
  2. A `failed` step leaves NO finding rows (worker bails before
     persisting).

Split out of test_research_executor.py because that file exceeded
the 300-line structural cap.
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
    sid = f"findings-{uuid4().hex[:8]}"
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
            "route": "deep", "reason": "test",
            "research_question_summary": "test", "plan": steps,
        },
        db_url=_db_url(),
    )


class _RichFinalAnswerLLM(BaseChatModel):
    """Returns a final_answer with summary + rows + mf_query +
    citations so the JSONB round-trip is observable end-to-end."""

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
                "args": {
                    "summary": "result text",
                    "rows": [{"branch": "A", "total": 100}],
                    "mf_query": {
                        "metric": "total_loan_balance",
                        "dimensions": ["branch"],
                    },
                    # Note: the `final_answer` tool signature
                    # doesn't currently accept citations — extra args
                    # are filtered out by langgraph. The worker
                    # callback reads payload.get("citations") which
                    # therefore stays None. Persistence column exists
                    # for forward-compat when the tool surface grows.
                },
                "id": "c1",
            }],
        ))])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _RichFinalAnswerLLM:
        return self


async def _drain(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for event in stream:
        out.append(event)
    return out


def test_complete_step_has_one_finding_with_full_jsonb_payload(
    thread_id: UUID,
) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "Pull loan balance by branch",
         "dependencies": []},
    ])
    expand_plan_into_steps(plan, db_url)
    asyncio.run(_drain(execute_plan_sequentially(
        plan_id=plan.plan_id, db_url=db_url, llm=_RichFinalAnswerLLM(),
    )))
    findings = steps_repo.get_findings_for_plan(plan.plan_id, db_url)
    assert len(findings) == 1
    f = findings[0]
    assert f.summary_text == "result text"
    assert f.structured_rows_json == [{"branch": "A", "total": 100}]
    assert f.mf_query_json is not None
    assert f.mf_query_json["metric"] == "total_loan_balance"
    # cited_artifacts: see comment above — currently None until the
    # final_answer tool signature accepts citations.
    assert f.cited_artifacts is None


def test_failed_step_leaves_no_finding_row(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id, [
        {"ordinal": 1, "description": "silent step", "dependencies": []},
    ])
    expand_plan_into_steps(plan, db_url)

    class _SilentLLM(_RichFinalAnswerLLM):
        def _generate(
            self, messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: CallbackManagerForLLMRun | None = None,
            **kwargs: Any,
        ) -> ChatResult:
            return ChatResult(generations=[
                ChatGeneration(message=AIMessage(content=""))
            ])

    asyncio.run(_drain(execute_plan_sequentially(
        plan_id=plan.plan_id, db_url=db_url, llm=_SilentLLM(),
    )))
    steps = steps_repo.get_steps_for_plan(plan.plan_id, db_url)
    assert all(s.status == "failed" for s in steps)
    assert steps_repo.get_findings_for_plan(plan.plan_id, db_url) == []
