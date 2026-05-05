"""Google AI Studio provider construction (HUG-196)."""

from __future__ import annotations

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from nl_engine.llm.providers.google import (
    DEFAULT_MODEL,
    GoogleProviderError,
    make_google_llm,
)


def test_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    llm = make_google_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model.endswith(DEFAULT_MODEL)


def test_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    llm = make_google_llm(model="gemma-3-27b-it")
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model.endswith("gemma-3-27b-it")


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(GoogleProviderError, match="GOOGLE_API_KEY"):
        make_google_llm()


def test_temperature_is_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    llm = make_google_llm()
    assert llm.temperature == 0
