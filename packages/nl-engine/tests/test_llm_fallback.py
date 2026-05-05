"""FallbackChatModel tests — rate-limit fall-through + error propagation (HUG-196)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from nl_engine.llm.fallback import FallbackChatModel, _is_rate_limit_error


class _StubLLM(BaseChatModel):
    """Test stub that returns a canned message or raises a configured exception."""

    label: str = "stub"
    raise_exc: BaseException | None = None
    bound_tools: list[Any] | None = None

    @property
    def _llm_type(self) -> str:
        return "stub-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.raise_exc is not None:
            raise self.raise_exc
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.label))],
        )

    def bind_tools(  # type: ignore[override]
        self,
        tools: Sequence[Any],
        **kwargs: Any,
    ) -> _StubLLM:
        # Return a copy with tools recorded so the test can inspect propagation.
        return _StubLLM(
            label=f"{self.label}-bound",
            raise_exc=self.raise_exc,
            bound_tools=list(tools),
        )


def test_primary_succeeds_no_fallback() -> None:
    primary = _StubLLM(label="primary")
    fallback = _StubLLM(label="fallback")
    chain = FallbackChatModel(primary=primary, fallback=fallback)
    msg = HumanMessage(content="hi")
    result = chain.invoke([msg])
    assert result.content == "primary"


def test_rate_limit_falls_through_429() -> None:
    primary = _StubLLM(label="primary", raise_exc=RuntimeError("HTTP 429 rate_limit"))
    fallback = _StubLLM(label="fallback")
    chain = FallbackChatModel(primary=primary, fallback=fallback)
    result = chain.invoke([HumanMessage(content="hi")])
    assert result.content == "fallback"


def test_rate_limit_falls_through_tpd() -> None:
    primary = _StubLLM(label="primary",
                       raise_exc=RuntimeError("tokens per day (TPD) limit"))
    fallback = _StubLLM(label="fallback")
    chain = FallbackChatModel(primary=primary, fallback=fallback)
    result = chain.invoke([HumanMessage(content="hi")])
    assert result.content == "fallback"


def test_non_rate_limit_propagates() -> None:
    primary = _StubLLM(label="primary",
                       raise_exc=RuntimeError("connection refused"))
    fallback = _StubLLM(label="fallback")
    chain = FallbackChatModel(primary=primary, fallback=fallback)
    with pytest.raises(RuntimeError, match="connection refused"):
        chain.invoke([HumanMessage(content="hi")])


def test_both_failing_surfaces_fallback_error() -> None:
    primary = _StubLLM(label="primary",
                       raise_exc=RuntimeError("HTTP 429 rate_limit"))
    fallback = _StubLLM(label="fallback",
                        raise_exc=RuntimeError("fallback exploded"))
    chain = FallbackChatModel(primary=primary, fallback=fallback)
    with pytest.raises(RuntimeError, match="fallback exploded"):
        chain.invoke([HumanMessage(content="hi")])


def test_bind_tools_propagates_to_both_legs() -> None:
    primary = _StubLLM(label="primary")
    fallback = _StubLLM(label="fallback")
    chain = FallbackChatModel(primary=primary, fallback=fallback)
    tools = [{"name": "foo"}]
    bound = chain.bind_tools(tools)
    assert isinstance(bound, FallbackChatModel)
    assert bound.primary.bound_tools == tools  # type: ignore[attr-defined]
    assert bound.fallback.bound_tools == tools  # type: ignore[attr-defined]


def test_is_rate_limit_error_detects_common_shapes() -> None:
    assert _is_rate_limit_error(RuntimeError("HTTP 429 something"))
    assert _is_rate_limit_error(RuntimeError("rate_limit_exceeded"))
    assert _is_rate_limit_error(RuntimeError("TPM exceeded"))
    assert _is_rate_limit_error(RuntimeError("quota"))
    assert not _is_rate_limit_error(RuntimeError("malformed input"))
    assert not _is_rate_limit_error(RuntimeError("auth failed"))
