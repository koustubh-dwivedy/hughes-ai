"""Generic OpenAI-compatible provider tests (HUG-206)."""

from __future__ import annotations

import pytest
from langchain_openai import ChatOpenAI
from nl_engine.llm.providers.openai_compatible import (
    DEFAULT_BASE_URL,
    OpenAICompatibleProviderError,
    make_openai_compatible_llm,
)


def test_construction_without_model_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unlike groq/google/ollama which have sensible default models,
    `openai_compatible` is generic — it can't know what model the
    target endpoint serves. Force the YAML to be explicit."""
    monkeypatch.setenv("CEREBRAS_API_KEY", "dummy")
    with pytest.raises(OpenAICompatibleProviderError, match="model"):
        make_openai_compatible_llm(api_key_env="CEREBRAS_API_KEY")


def test_construction_without_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The provider reads the env-var NAME from config, not the value
    directly. If the named var isn't set, raise with a message that
    names the missing var."""
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    with pytest.raises(
        OpenAICompatibleProviderError, match="CEREBRAS_API_KEY"
    ):
        make_openai_compatible_llm(
            model="zai-glm-4.7", api_key_env="CEREBRAS_API_KEY"
        )


def test_construction_with_api_key_returns_chat_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CEREBRAS_API_KEY", "dummy-key")
    monkeypatch.delenv("CEREBRAS_BASE_URL", raising=False)
    llm = make_openai_compatible_llm(
        model="zai-glm-4.7",
        api_key_env="CEREBRAS_API_KEY",
        base_url_env="CEREBRAS_BASE_URL",
    )
    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "zai-glm-4.7"
    # When base_url_env is unset, the provider falls back to the
    # Cerebras default.
    assert str(llm.openai_api_base) == DEFAULT_BASE_URL
    assert llm.temperature == 0


def test_base_url_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """The point of base_url_env is endpoint portability — the same
    provider module should reach Cerebras, Together, Fireworks, etc.
    by changing nothing but the YAML."""
    monkeypatch.setenv("FIREWORKS_API_KEY", "dummy")
    monkeypatch.setenv(
        "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
    )
    llm = make_openai_compatible_llm(
        model="accounts/fireworks/models/llama-v3p1-70b-instruct",
        api_key_env="FIREWORKS_API_KEY",
        base_url_env="FIREWORKS_BASE_URL",
    )
    assert isinstance(llm, ChatOpenAI)
    assert (
        str(llm.openai_api_base) == "https://api.fireworks.ai/inference/v1"
    )


def test_default_base_url_is_cerebras() -> None:
    """Cerebras was the first non-OpenAI use case for this provider, so
    the default base URL points there. Any other endpoint sets
    base_url_env in the YAML to override."""
    assert DEFAULT_BASE_URL == "https://api.cerebras.ai/v1"


def test_api_key_env_indirection_with_custom_var_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ops can use any env var name they like — `MY_CUSTOM_KEY`,
    `PROD_LLM_TOKEN`, whatever — by setting it as `api_key_env` in
    config/llm.yaml. This isolates the YAML from credential naming
    conventions."""
    monkeypatch.setenv("MY_CUSTOM_KEY", "secret")
    llm = make_openai_compatible_llm(
        model="some-model", api_key_env="MY_CUSTOM_KEY"
    )
    assert isinstance(llm, ChatOpenAI)
