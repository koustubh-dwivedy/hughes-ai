"""Factory dispatch + fallback chain wiring (HUG-196)."""

from __future__ import annotations

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from nl_engine.llm import LLMConfig, make_llm
from nl_engine.llm.factory import LLMFactoryError, _read_provider, _resolve_config
from nl_engine.llm.fallback import FallbackChatModel


def _set_env(monkeypatch: pytest.MonkeyPatch, **vars: str | None) -> None:
    for k in ("LLM_PROVIDER", "LLM_FALLBACK_PROVIDER", "LLM_MODEL",
              "GROQ_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in vars.items():
        if v is not None:
            monkeypatch.setenv(k, v)


def test_default_provider_is_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, GROQ_API_KEY="dummy")
    llm = make_llm()
    assert isinstance(llm, ChatGroq)


def test_explicit_google_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, LLM_PROVIDER="google", GOOGLE_API_KEY="dummy")
    llm = make_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)


def test_fallback_chain_wraps(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(
        monkeypatch,
        LLM_PROVIDER="groq",
        LLM_FALLBACK_PROVIDER="google",
        GROQ_API_KEY="dummy",
        GOOGLE_API_KEY="dummy",
    )
    llm = make_llm()
    assert isinstance(llm, FallbackChatModel)
    assert isinstance(llm.primary, ChatGroq)
    assert isinstance(llm.fallback, ChatGoogleGenerativeAI)


def test_invalid_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, LLM_PROVIDER="not-a-provider", GROQ_API_KEY="dummy")
    with pytest.raises(LLMFactoryError):
        make_llm()


def test_same_primary_and_fallback_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(
        monkeypatch,
        LLM_PROVIDER="groq",
        LLM_FALLBACK_PROVIDER="groq",
        GROQ_API_KEY="dummy",
    )
    with pytest.raises(LLMFactoryError):
        make_llm()


def test_programmatic_config_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLMConfig passed directly bypasses env-var resolution."""
    _set_env(monkeypatch, LLM_PROVIDER="groq", GROQ_API_KEY="dummy",
             GOOGLE_API_KEY="dummy")
    llm = make_llm(LLMConfig(provider="google"))
    assert isinstance(llm, ChatGoogleGenerativeAI)


def test_read_provider_default_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("X", raising=False)
    assert _read_provider("X", "groq") == "groq"
    assert _read_provider("X", None) is None


def test_read_provider_lowercases_and_validates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("X", "GOOGLE")
    assert _read_provider("X", None) == "google"
    monkeypatch.setenv("X", "openai")
    with pytest.raises(LLMFactoryError):
        _read_provider("X", None)


def test_resolve_config_reads_model_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, LLM_PROVIDER="groq", LLM_MODEL="custom/model")
    cfg = _resolve_config()
    assert cfg.provider == "groq"
    assert cfg.model == "custom/model"
