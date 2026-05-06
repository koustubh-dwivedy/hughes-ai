"""Factory dispatch — single-LLM, config-file driven (HUG-190 Phase E)."""

from __future__ import annotations

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from nl_engine.llm import LLMConfig, make_llm
from nl_engine.llm.factory import (
    LLMFactoryError,
    _read_env_config,
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
