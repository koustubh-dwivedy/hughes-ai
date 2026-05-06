"""Ollama provider construction tests (HUG-190 Phase E)."""

from __future__ import annotations

import pytest
from langchain_ollama import ChatOllama
from nl_engine.llm.providers.ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OllamaProviderError,
    make_ollama_llm,
)


def test_construction_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    with pytest.raises(OllamaProviderError, match="OLLAMA_API_KEY"):
        make_ollama_llm()


def test_construction_with_api_key_returns_chat_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "dummy-key")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    llm = make_ollama_llm()
    assert isinstance(llm, ChatOllama)
    assert llm.model == DEFAULT_MODEL
    assert llm.base_url == DEFAULT_BASE_URL


def test_explicit_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "dummy-key")
    llm = make_ollama_llm(model="qwen3-next:80b")
    assert isinstance(llm, ChatOllama)
    assert llm.model == "qwen3-next:80b"


def test_base_url_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "dummy-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = make_ollama_llm()
    assert isinstance(llm, ChatOllama)
    assert llm.base_url == "http://localhost:11434"


def test_auth_header_threaded_into_client_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key-xyz")
    llm = make_ollama_llm()
    # `ChatOllama` stores client_kwargs verbatim; the bearer header
    # appears in every request the underlying client makes.
    assert llm.client_kwargs is not None
    headers = llm.client_kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer test-key-xyz"


def test_default_timeout_in_client_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """HUG-190 2026-05-07: explicit HTTP timeout prevents Ollama hang."""
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    monkeypatch.delenv("OLLAMA_TIMEOUT_S", raising=False)
    llm = make_ollama_llm()
    assert llm.client_kwargs is not None
    assert llm.client_kwargs.get("timeout") == 120.0


def test_timeout_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    monkeypatch.setenv("OLLAMA_TIMEOUT_S", "30")
    llm = make_ollama_llm()
    assert llm.client_kwargs is not None
    assert llm.client_kwargs.get("timeout") == 30.0
