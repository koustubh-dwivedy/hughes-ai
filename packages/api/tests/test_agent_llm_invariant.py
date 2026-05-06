"""Invariant: `make_agent_llm()` follows `config/llm.yaml` (HUG-190 single-LLM
config-driven refactor, 2026-05-07). The single source of truth for the
agent's LLM identity is the YAML — env vars are a fallback for tests only.

This test exists to prevent silent regressions where someone hard-codes a
provider in the factory (which would bypass the user's config). Concrete
provider behaviors (e.g., Qwen's `reasoning_format='hidden'`) live with
the provider's own tests, not here.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _provider_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider constructors validate credentials at instantiation time;
    set dummies for every supported provider so make_llm() can construct
    whichever one config/llm.yaml selects without a network call."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")


def _read_configured_provider() -> tuple[str, str]:
    """Return (provider, model) from config/llm.yaml. Done by the test —
    not the factory — so we can assert the factory honored the file."""
    from pathlib import Path

    import yaml

    cfg_path = (
        Path(__file__).resolve().parents[3] / "config" / "llm.yaml"
    )
    cfg = yaml.safe_load(cfg_path.read_text())
    return cfg["provider"], cfg.get("model") or ""


def test_make_agent_llm_honors_config_yaml() -> None:
    """The agent's LLM identity matches `config/llm.yaml`."""
    from api.services.llm import make_agent_llm

    provider, model = _read_configured_provider()
    llm = make_agent_llm()
    type_name = type(llm).__name__.lower()
    expected_class_substring = {
        "groq": "groq",
        "google": "google",
        "ollama": "ollama",
    }[provider]
    assert expected_class_substring in type_name, (
        f"config/llm.yaml selects provider={provider!r} but make_agent_llm "
        f"returned {type(llm).__name__}. Factory is bypassing config."
    )
    actual_model = (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or ""
    )
    if model:
        assert model in str(actual_model), (
            f"config/llm.yaml selects model={model!r} but the constructed "
            f"LLM reports model={actual_model!r}."
        )
