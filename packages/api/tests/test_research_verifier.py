"""Verifier tests (HUG-223, V1).

Covers:
  1. is_enabled() returns False without the env flag.
  2. is_enabled() returns True when env flag is set.
  3. verify() with consistent answer → flagged=False.
  4. verify() with contradiction → flagged=True with reason.
  5. Parse failure → safe-default to flagged=False.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from api.services.research_agent.verifier import (
    VerifierVerdict,
    is_enabled,
    verify,
)
from api.types.research import Finding
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class _ScriptedLLM(BaseChatModel):
    response: str

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(
        self, messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[
            ChatGeneration(message=AIMessage(content=self.response))
        ])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _ScriptedLLM:
        return self


def _finding(rows: list[dict[str, Any]]) -> Finding:
    return Finding(
        finding_id=uuid4(),
        step_id=uuid4(),
        summary_text="step summary",
        structured_rows_json=rows,
        created_at=datetime.now(UTC),
    )


def test_is_enabled_false_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCH_VERIFIER_ENABLED", raising=False)
    assert is_enabled() is False


def test_is_enabled_true_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_VERIFIER_ENABLED", "1")
    assert is_enabled() is True


def test_consistent_summary_yields_no_flag() -> None:
    llm = _ScriptedLLM(response='{"flagged": false, "reason": ""}')
    verdict = verify(
        summary="Loan balance grew 10% YoY",
        findings=[_finding([{"yoy_pct": 10.5}])],
        llm=llm,
    )
    assert isinstance(verdict, VerifierVerdict)
    assert verdict.flagged is False


def test_contradicting_summary_is_flagged() -> None:
    llm = _ScriptedLLM(
        response=(
            '{"flagged": true, "reason":'
            ' "summary says increase but rows show decrease"}'
        )
    )
    verdict = verify(
        summary="Loan balance grew 10% YoY",
        findings=[_finding([{"yoy_pct": -5.0}])],
        llm=llm,
    )
    assert verdict.flagged is True
    assert "decrease" in verdict.reason


def test_parse_failure_safe_defaults_to_not_flagged() -> None:
    """Verifier should never block the answer for flakiness."""
    llm = _ScriptedLLM(response="this is not json")
    verdict = verify(
        summary="x", findings=[_finding([{}])], llm=llm,
    )
    assert verdict.flagged is False
    assert "parse_failed" in verdict.reason
