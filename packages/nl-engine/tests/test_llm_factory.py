"""Factory dispatch — single-LLM, config-file driven (HUG-190 Phase E)."""

from __future__ import annotations

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from nl_engine.llm import LLMConfig, make_llm
from nl_engine.llm.factory import (
    LLMFactoryError,
    _read_env_config,
    _read_yaml_config,
    _validate_provider,
)


def _set_env(monkeypatch: pytest.MonkeyPatch, **vars: str | None) -> None:
    for k in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "GROQ_API_KEY",
        "GOOGLE_API_KEY",
        "OLLAMA_API_KEY",
        "OLLAMA_BASE_URL",
        "CEREBRAS_API_KEY",
        "CEREBRAS_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(k, raising=False)
    for k, v in vars.items():
        if v is not None:
            monkeypatch.setenv(k, v)


def test_default_provider_is_groq_when_yaml_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """When config/llm.yaml is absent and no env override is set,
    the factory falls back to the env-default provider (groq)."""
    _set_env(monkeypatch, GROQ_API_KEY="dummy")
    # Force YAML lookup to a non-existent path to simulate absence.
    monkeypatch.setattr(
        "nl_engine.llm.factory._CONFIG_PATH",
        tmp_path_factory.mktemp("nope") / "missing.yaml",
    )
    llm = make_llm()
    assert isinstance(llm, ChatGroq)


def test_explicit_google_via_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    _set_env(monkeypatch, LLM_PROVIDER="google", GOOGLE_API_KEY="dummy")
    monkeypatch.setattr(
        "nl_engine.llm.factory._CONFIG_PATH",
        tmp_path_factory.mktemp("nope") / "missing.yaml",
    )
    llm = make_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)


def test_explicit_ollama_via_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    _set_env(monkeypatch, LLM_PROVIDER="ollama", OLLAMA_API_KEY="dummy")
    monkeypatch.setattr(
        "nl_engine.llm.factory._CONFIG_PATH",
        tmp_path_factory.mktemp("nope") / "missing.yaml",
    )
    llm = make_llm()
    assert isinstance(llm, ChatOllama)


def test_yaml_config_drives_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """When config/llm.yaml exists, it wins over env vars."""
    _set_env(
        monkeypatch,
        LLM_PROVIDER="groq",
        GROQ_API_KEY="dummy",
        OLLAMA_API_KEY="dummy",
    )
    yaml_path = tmp_path / "llm.yaml"
    yaml_path.write_text(
        "provider: ollama\nmodel: qwen3-coder:480b\napi_key_env: OLLAMA_API_KEY\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    llm = make_llm()
    assert isinstance(llm, ChatOllama)


def test_invalid_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(LLMFactoryError):
        _validate_provider("not-a-provider", source="test")


def test_validate_provider_lowercases() -> None:
    assert _validate_provider("OLLAMA", source="test") == "ollama"
    assert _validate_provider("Google", source="test") == "google"


def test_programmatic_config_overrides_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """LLMConfig passed directly bypasses both YAML and env vars."""
    _set_env(monkeypatch, LLM_PROVIDER="groq", GROQ_API_KEY="dummy",
             GOOGLE_API_KEY="dummy")
    monkeypatch.setattr(
        "nl_engine.llm.factory._CONFIG_PATH",
        tmp_path_factory.mktemp("nope") / "missing.yaml",
    )
    llm = make_llm(LLMConfig(provider="google"))
    assert isinstance(llm, ChatGoogleGenerativeAI)


def test_env_config_reads_model_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, LLM_PROVIDER="groq", LLM_MODEL="custom/model")
    cfg = _read_env_config()
    assert cfg.provider == "groq"
    assert cfg.model == "custom/model"


def test_yaml_invalid_provider_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    yaml_path = tmp_path / "llm.yaml"
    yaml_path.write_text("provider: not-a-provider\n", encoding="utf-8")
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    with pytest.raises(LLMFactoryError):
        make_llm()


# HUG-206 — generic openai_compatible provider lets new endpoints
# (Cerebras, Together, Fireworks, vLLM, OpenAI itself) be added by
# config-file change alone. The factory dispatches to the same module
# regardless of which endpoint the YAML names.


def test_yaml_dispatches_to_openai_compatible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """End-to-end: write a YAML pointing at Cerebras/GLM, set the env
    vars it names, call make_llm() — expect a ChatOpenAI pointed at
    the right base_url with the right model."""
    _set_env(
        monkeypatch,
        CEREBRAS_API_KEY="dummy-key",
        CEREBRAS_BASE_URL="https://api.cerebras.ai/v1",
    )
    yaml_path = tmp_path / "llm.yaml"
    yaml_path.write_text(
        "provider: openai_compatible\n"
        "model: zai-glm-4.7\n"
        "api_key_env: CEREBRAS_API_KEY\n"
        "base_url_env: CEREBRAS_BASE_URL\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    llm = make_llm()
    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "zai-glm-4.7"
    assert str(llm.openai_api_base) == "https://api.cerebras.ai/v1"


def test_yaml_reads_api_key_env_and_base_url_env(
    tmp_path: pytest.TempPathFactory,
) -> None:
    yaml_path = tmp_path / "llm.yaml"
    yaml_path.write_text(
        "provider: openai_compatible\n"
        "model: some/model\n"
        "api_key_env: MY_TOKEN\n"
        "base_url_env: MY_ENDPOINT\n",
        encoding="utf-8",
    )
    import nl_engine.llm.factory as factory_mod  # noqa: PLC0415

    original = factory_mod._CONFIG_PATH
    factory_mod._CONFIG_PATH = yaml_path
    try:
        cfg = _read_yaml_config()
    finally:
        factory_mod._CONFIG_PATH = original
    assert cfg is not None
    assert cfg.provider == "openai_compatible"
    assert cfg.model == "some/model"
    assert cfg.api_key_env == "MY_TOKEN"
    assert cfg.base_url_env == "MY_ENDPOINT"


def test_validate_provider_accepts_openai_compatible() -> None:
    assert _validate_provider("openai_compatible", source="t") == (
        "openai_compatible"
    )


def test_explicit_llmconfig_for_openai_compatible_bypasses_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Tests / scripts can pass an explicit LLMConfig and skip both
    the YAML and the env-var fallback path."""
    _set_env(monkeypatch, CEREBRAS_API_KEY="dummy")
    monkeypatch.setattr(
        "nl_engine.llm.factory._CONFIG_PATH",
        tmp_path_factory.mktemp("nope") / "missing.yaml",
    )
    llm = make_llm(
        LLMConfig(
            provider="openai_compatible",
            model="zai-glm-4.7",
            api_key_env="CEREBRAS_API_KEY",
            base_url_env="CEREBRAS_BASE_URL",
        )
    )
    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "zai-glm-4.7"
