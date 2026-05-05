"""Groq provider construction (HUG-196)."""

from __future__ import annotations

import pytest
from langchain_groq import ChatGroq
from nl_engine.llm.providers.groq import (
    DEFAULT_MODEL,
    GroqProviderError,
    make_groq_llm,
)


def test_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    llm = make_groq_llm()
    assert isinstance(llm, ChatGroq)
    assert llm.model_name == DEFAULT_MODEL


def test_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    llm = make_groq_llm(model="qwen/qwen3-235b-a22b-instruct-2507")
    assert isinstance(llm, ChatGroq)
    assert llm.model_name == "qwen/qwen3-235b-a22b-instruct-2507"


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(GroqProviderError, match="GROQ_API_KEY"):
        make_groq_llm()


def test_temperature_is_zero_per_adr(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0004 invariant — deterministic. ChatGroq coerces 0 → 1e-08 internally
    (Groq's API rejects true zero on some models); both are deterministic."""
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    llm = make_groq_llm()
    assert llm.temperature is not None and llm.temperature <= 1e-7


def test_reasoning_format_is_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0004 invariant — reasoning_format='hidden' to prevent CoT leak."""
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    llm = make_groq_llm()
    assert getattr(llm, "reasoning_format", None) == "hidden"
