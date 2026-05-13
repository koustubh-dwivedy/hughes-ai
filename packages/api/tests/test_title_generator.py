"""Unit tests for the LLM-backed sidebar title generator."""

from __future__ import annotations

from typing import Any

from api.services.title_generator import generate_title
from langchain_core.messages import AIMessage


class _FakeLLM:
    """Minimal stand-in for BaseChatModel; returns whatever content we
    set on the instance. Tests don't need the real Ollama round-trip."""

    def __init__(self, content: str | Any, raises: Exception | None = None) -> None:
        self._content = content
        self._raises = raises

    def invoke(self, _messages: Any, **_kwargs: Any) -> Any:
        if self._raises is not None:
            raise self._raises
        return AIMessage(content=self._content)


def test_generate_title_returns_clean_string_from_llm() -> None:
    llm = _FakeLLM("Loan delinquency by product")
    assert generate_title("How's delinquency by product?", llm) == (
        "Loan delinquency by product"
    )


def test_generate_title_strips_wrapping_quotes() -> None:
    llm = _FakeLLM('"Q1 origination trends"')
    assert generate_title("Show Q1 origination trends", llm) == "Q1 origination trends"


def test_generate_title_strips_trailing_period() -> None:
    llm = _FakeLLM("Branch loan portfolio mix.")
    assert generate_title("loans by branch", llm) == "Branch loan portfolio mix"


def test_generate_title_strips_title_prefix() -> None:
    llm = _FakeLLM("Title: Approval rate this quarter")
    assert generate_title("approval rate?", llm) == "Approval rate this quarter"


def test_generate_title_falls_back_on_multi_line_output() -> None:
    llm = _FakeLLM("Line one\nLine two\nLine three")
    # Falls back to first 6 words of the input.
    assert generate_title("How are we doing this month overall today", llm) == (
        "How are we doing this month"
    )


def test_generate_title_falls_back_on_oversized_output() -> None:
    llm = _FakeLLM("A" * 200)  # 200 chars, way over the 60-char cap.
    assert generate_title("Q1 originations by product", llm) == (
        "Q1 originations by product"
    )


def test_generate_title_falls_back_on_llm_exception() -> None:
    llm = _FakeLLM("", raises=RuntimeError("ollama down"))
    assert generate_title("Show me the rate spread for April", llm) == (
        "Show me the rate spread for"
    )


def test_generate_title_handles_empty_input() -> None:
    llm = _FakeLLM("anything")
    assert generate_title("", llm) == "Untitled chat"


def test_generate_title_handles_list_content() -> None:
    """Some chat models return content as a list of parts."""
    llm = _FakeLLM([{"text": "Mortgage portfolio composition"}])
    assert generate_title("first mortgage breakdown", llm) == (
        "Mortgage portfolio composition"
    )
