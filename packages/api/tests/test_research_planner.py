"""Lead planner tests (HUG-208, L1).

Pure-Python; no DB or live LLM. A stub LLM lets us drive every
parse / validate / retry path deterministically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from api.prometheus import research_telemetry_events_total
from api.services.research_agent.planner import (
    PlannerError,
    draft_plan,
)
from api.services.research_agent.telemetry import (
    EVENT_PLAN_DRAFT_FAILED,
    EVENT_PLAN_DRAFTED,
)
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class _ScriptedLLM(BaseChatModel):
    """LLM that returns predetermined string responses in order."""

    responses: list[str]
    call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=self.responses[idx]))
            ]
        )

    def bind_tools(  # type: ignore[override]
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _ScriptedLLM:
        return self


def _shallow_json() -> str:
    return (
        '{"route": "shallow", "reason": "single metric, single window",'
        ' "plan": null, "research_question_summary": "current delinquency"}'
    )


def _deep_json(n_steps: int = 4) -> str:
    steps = [
        {
            "ordinal": i + 1,
            "description": f"step {i + 1}",
            "dependencies": [] if i == 0 else [i],
        }
        for i in range(n_steps)
    ]
    import json as _json

    return _json.dumps(
        {
            "route": "deep",
            "reason": "multi-step decomposition needed",
            "plan": steps,
            "research_question_summary": "drivers analysis",
        }
    )


# ---- happy paths --------------------------------------------------


def test_shallow_response_parses_to_pland_draft_with_no_plan() -> None:
    llm = _ScriptedLLM(responses=[_shallow_json()])
    draft = draft_plan("What's our delinquency rate?", [], llm)
    assert draft.route == "shallow"
    assert draft.plan is None
    assert draft.reason == "single metric, single window"


def test_deep_response_parses_steps_and_dependencies() -> None:
    llm = _ScriptedLLM(responses=[_deep_json(4)])
    draft = draft_plan("Decompose NIM YTD", [], llm)
    assert draft.route == "deep"
    assert draft.plan is not None
    assert len(draft.plan) == 4
    assert draft.plan[0].ordinal == 1
    assert draft.plan[0].dependencies == []
    assert draft.plan[3].dependencies == [3]


def test_code_fenced_response_is_still_parsed() -> None:
    """Providers occasionally wrap JSON in ```json…``` despite the
    prompt saying not to. The planner strips fences before parsing."""
    fenced = f"```json\n{_shallow_json()}\n```"
    llm = _ScriptedLLM(responses=[fenced])
    draft = draft_plan("question", [], llm)
    assert draft.route == "shallow"


# ---- retry / failure paths ----------------------------------------


def test_malformed_first_retries_then_succeeds() -> None:
    """First response: garbage. Second response: valid. Planner
    succeeds on attempt 2."""
    llm = _ScriptedLLM(responses=["this is not json at all", _shallow_json()])
    draft = draft_plan("Q", [], llm)
    assert draft.route == "shallow"
    assert llm.call_count == 2


def test_two_consecutive_malformed_raises_planner_error() -> None:
    llm = _ScriptedLLM(responses=["nope", "still nope"])
    before = research_telemetry_events_total.labels(
        event_name=EVENT_PLAN_DRAFT_FAILED
    )._value.get()  # type: ignore[attr-defined]
    with pytest.raises(PlannerError):
        draft_plan("Q", [], llm)
    after = research_telemetry_events_total.labels(
        event_name=EVENT_PLAN_DRAFT_FAILED
    )._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_deep_route_without_plan_field_rejected() -> None:
    """Schema enforcement: route='deep' MUST come with a non-empty
    plan list. The model validator rejects mismatches."""
    bad = (
        '{"route": "deep", "reason": "x", "plan": null,'
        ' "research_question_summary": "y"}'
    )
    llm = _ScriptedLLM(responses=[bad, bad])  # both attempts fail
    with pytest.raises(PlannerError):
        draft_plan("Q", [], llm)


def test_shallow_route_with_plan_field_rejected() -> None:
    """Mirror constraint: shallow MUST NOT carry a plan."""
    bad = (
        '{"route": "shallow", "reason": "x",'
        ' "plan": [{"ordinal": 1, "description": "x",'
        ' "dependencies": []}],'
        ' "research_question_summary": "y"}'
    )
    llm = _ScriptedLLM(responses=[bad, bad])
    with pytest.raises(PlannerError):
        draft_plan("Q", [], llm)


def test_unknown_route_value_rejected() -> None:
    """`route` must be exactly 'shallow' or 'deep'."""
    bad = (
        '{"route": "medium", "reason": "x", "plan": null,'
        ' "research_question_summary": "y"}'
    )
    llm = _ScriptedLLM(responses=[bad, bad])
    with pytest.raises(PlannerError):
        draft_plan("Q", [], llm)


# ---- telemetry ----------------------------------------------------


def test_success_emits_plan_drafted_event() -> None:
    before = research_telemetry_events_total.labels(
        event_name=EVENT_PLAN_DRAFTED
    )._value.get()  # type: ignore[attr-defined]
    llm = _ScriptedLLM(responses=[_deep_json(3)])
    draft_plan("Q", [], llm)
    after = research_telemetry_events_total.labels(
        event_name=EVENT_PLAN_DRAFTED
    )._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


# ---- history compression ------------------------------------------


def test_long_history_does_not_blow_prompt() -> None:
    """A thread with 100 long messages must not feed the planner a
    20K-char prompt. The history compression keeps it bounded at
    ~4K chars (latest exchanges)."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from api.types.threads import ThreadMessage

    history = [
        ThreadMessage(
            message_id=uuid4(),
            thread_id=uuid4(),
            role="user" if i % 2 == 0 else "assistant",
            content="long message " * 50,
            created_at=datetime.now(UTC),
        )
        for i in range(100)
    ]
    llm = _ScriptedLLM(responses=[_shallow_json()])
    draft = draft_plan("Q", history, llm)
    assert draft.route == "shallow"
