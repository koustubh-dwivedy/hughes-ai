"""Re-plan logic tests (HUG-221, M2).

Covers the decision + persistence primitives:
  1. revise=false LLM verdict → no new plan persisted.
  2. revise=true with new_plan → new plan_json persisted, old marked
     superseded, version increments.
  3. MAX_PLAN_VERSIONS cap kicks in on the 6th attempt.
  4. Malformed LLM JSON → parser retries → on second failure returns
     ReviseDecision(revise=False).
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import research as research_repo
from api.repo import threads as threads_repo
from api.services.research_agent.replanner import (
    ReviseDecision,
    decide_revise,
    revise_plan,
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
    sid = f"rep-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url, user_id=sid)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM research_plans WHERE thread_id = %s",
                    (str(thread.thread_id),))
        cur.execute("DELETE FROM threads WHERE thread_id = %s",
                    (str(thread.thread_id),))
        conn.commit()


def _seed_plan(thread_id: UUID, version: int = 1) -> Any:
    p = research_repo.create_plan(
        thread_id=thread_id, plan_json={
            "route": "deep", "reason": "test",
            "plan": [{"ordinal": 1, "description": "x", "dependencies": []}],
        }, db_url=_db_url(), version=version,
    )
    research_repo.update_plan_status(p.plan_id, "running", _db_url())
    return research_repo.get_plan(p.plan_id, _db_url())


class _ScriptedLLM(BaseChatModel):
    """Returns predetermined string responses in order."""

    responses: list[str]
    call_idx: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(
        self, messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        i = min(self.call_idx, len(self.responses) - 1)
        self.call_idx += 1
        return ChatResult(generations=[
            ChatGeneration(message=AIMessage(content=self.responses[i]))
        ])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _ScriptedLLM:
        return self


def test_revise_false_persists_no_new_plan(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    llm = _ScriptedLLM(responses=[
        '{"revise": false, "reason": "findings consistent", "new_plan": null}'
    ])
    decision = decide_revise(plan, findings=[], lead_note="", llm=llm)
    assert decision.revise is False
    new = revise_plan(plan=plan, decision=decision, db_url=db_url)
    assert new is None
    versions = research_repo.list_plan_versions(thread_id, db_url)
    assert len(versions) == 1
    assert versions[0].status == "running"


def test_revise_true_persists_new_version(thread_id: UUID) -> None:
    db_url = _db_url()
    plan = _seed_plan(thread_id)
    llm = _ScriptedLLM(responses=[
        '{"revise": true, "reason": "data unavailable for step 1",'
        ' "new_plan": ['
        '   {"ordinal": 1, "description": "alt-step", "dependencies": []},'
        '   {"ordinal": 2, "description": "alt-step-2", "dependencies": [1]}'
        ' ]}'
    ])
    decision = decide_revise(plan, findings=[], lead_note="", llm=llm)
    assert decision.revise is True
    new = revise_plan(plan=plan, decision=decision, db_url=db_url)
    assert new is not None
    assert new.version == 2
    assert new.status == "approved"
    assert len(new.plan_json["plan"]) == 2
    # Old plan flipped to superseded.
    old = research_repo.get_plan(plan.plan_id, db_url)
    assert old is not None
    assert old.status == "superseded"


def test_max_plan_versions_cap(thread_id: UUID) -> None:
    """When current plan's version == MAX_PLAN_VERSIONS, no revise."""
    db_url = _db_url()
    plan = _seed_plan(thread_id, version=5)   # at the cap
    decision = ReviseDecision(
        revise=True, reason="x",
        new_plan=[{"ordinal": 1, "description": "y", "dependencies": []}],
    )
    new = revise_plan(plan=plan, decision=decision, db_url=db_url)
    assert new is None
    # Original plan unchanged.
    persisted = research_repo.get_plan(plan.plan_id, db_url)
    assert persisted is not None
    assert persisted.status == "running"


def test_parse_failure_returns_no_revise(thread_id: UUID) -> None:
    plan = _seed_plan(thread_id)
    llm = _ScriptedLLM(responses=["this is not json", "still not json"])
    decision = decide_revise(plan, findings=[], lead_note="", llm=llm)
    assert decision.revise is False
    assert "parse_failed" in decision.reason
