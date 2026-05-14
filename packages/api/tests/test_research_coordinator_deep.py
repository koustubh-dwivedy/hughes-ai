"""Coordinator deep-route persistence tests (HUG-209, L2).

Mirrors the live-Postgres + stubbed-LLM pattern of
`test_research_coordinator.py` (which covers the shallow path).
Split into its own file so each module stays under the 300-line
structural cap.
"""

from __future__ import annotations

import asyncio
import json as _json
import os
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import research as research_repo
from api.repo import threads as threads_repo
from api.services.research_agent import coordinator
from api.services.research_agent.coordinator import route_turn
from api.services.research_agent.planner import PlanDraft
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")


class _FinalAnswerLLM(BaseChatModel):
    """Deterministic stub — never actually called on deep path since
    the planner is also stubbed, but route_turn's signature requires
    one."""

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
                "args": {"summary": "ok", "rows": []},
                "id": "c1",
            }],
        ))])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FinalAnswerLLM:
        return self


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> UUID:
    db_url = _db_url()
    sid = f"pytest-deep-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url)
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


@pytest.fixture
def stub_deep_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    """3-step plan with a dep edge; matches Anthropic-style typical shape."""

    def _stub(_q: str, _h: Any, _l: Any) -> PlanDraft:
        return PlanDraft(
            route="deep",
            reason="stub-deep",
            plan=[
                {"ordinal": 1, "description": "Pull metric A", "dependencies": []},
                {"ordinal": 2, "description": "Pull metric B", "dependencies": []},
                {
                    "ordinal": 3,
                    "description": "Compare A and B",
                    "dependencies": [1, 2],
                },
            ],
            research_question_summary="three-step decomposition",
        )

    monkeypatch.setattr(coordinator, "draft_plan", _stub)


@pytest.fixture
def stub_shallow_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    def _stub(_q: str, _h: Any, _l: Any) -> PlanDraft:
        return PlanDraft(
            route="shallow", reason="stub-shallow", plan=None,
            research_question_summary="stub",
        )

    monkeypatch.setattr(coordinator, "draft_plan", _stub)


async def _drain(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for event in stream:
        out.append(event)
    return out


def test_deep_route_persists_plan_and_emits_plan_drafted(
    thread_id: UUID, stub_deep_planner: None
) -> None:
    """A deep-route turn writes exactly one research_plans row with
    status='draft' + version=1, and yields exactly one SSE event of
    type `research.plan.drafted` whose plan_id matches that row."""
    db_url = _db_url()
    events = asyncio.run(
        _drain(
            route_turn(
                thread_id=thread_id,
                user_content="audit drivers of past-due delta",
                db_url=db_url,
                llm=_FinalAnswerLLM(),
                history=[],
                request_id="rid-deep",
            )
        )
    )
    assert len(events) == 1, [e["event"] for e in events]
    assert events[0]["event"] == "research.plan.drafted"

    payload = _json.loads(events[0]["data"])
    plan_id = UUID(payload["plan_id"])
    assert payload["thread_id"] == str(thread_id)
    assert payload["version"] == 1
    assert payload["status"] == "draft"

    latest = research_repo.get_latest_plan(thread_id, db_url)
    assert latest is not None
    assert latest.plan_id == plan_id
    assert latest.version == 1
    assert latest.status == "draft"
    assert latest.plan_json["route"] == "deep"
    assert len(latest.plan_json["plan"]) == 3


def test_shallow_route_writes_no_plan_row(
    thread_id: UUID, stub_shallow_planner: None
) -> None:
    """Shallow turns must NOT write to research_plans (deep-only)."""
    db_url = _db_url()
    asyncio.run(
        _drain(
            route_turn(
                thread_id=thread_id,
                user_content="single-shot question",
                db_url=db_url,
                llm=_FinalAnswerLLM(),
                history=[],
            )
        )
    )
    assert research_repo.get_latest_plan(thread_id, db_url) is None
