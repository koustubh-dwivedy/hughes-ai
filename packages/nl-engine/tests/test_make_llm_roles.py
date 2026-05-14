"""Per-role `make_llm` extension (HUG-204).

Verifies:
  - `make_llm()` (no role) is unchanged — back-compat with every
    existing call site.
  - `make_llm(role=…)` with no `roles:` block falls back to the
    top-level config (ADR-0004 single-LLM default still wins).
  - `make_llm(role=…)` with the role present in `roles:` uses that.
  - `make_llm(role="worker"|"verifier")` falls back to
    `roles.lead` when its own entry is missing.
  - Unknown role string raises `ValueError`.
  - Malformed `roles:` block (missing `provider`) raises
    `LLMFactoryError`.
"""

from __future__ import annotations

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from nl_engine.llm import make_llm
from nl_engine.llm.factory import LLMFactoryError, _read_yaml_config


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


def _write_yaml(tmp_path: pytest.TempPathFactory, body: str) -> str:
    yaml_path = tmp_path / "llm.yaml"  # type: ignore[operator]
    yaml_path.write_text(body, encoding="utf-8")
    return yaml_path  # type: ignore[return-value]


def test_no_role_returns_top_level_llm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Back-compat: existing `make_llm()` callers see no change."""
    _set_env(monkeypatch, GROQ_API_KEY="dummy")
    yaml_path = _write_yaml(
        tmp_path, "provider: groq\nmodel: qwen/qwen3-32b\n"
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    llm = make_llm()
    assert isinstance(llm, ChatGroq)


def test_role_with_no_roles_block_falls_back_to_top_level(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """`role` is opt-in. With no `roles:` block, role-aware calls
    behave identically to top-level resolution (ADR-0004 default)."""
    _set_env(monkeypatch, GROQ_API_KEY="dummy")
    yaml_path = _write_yaml(
        tmp_path, "provider: groq\nmodel: qwen/qwen3-32b\n"
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    assert isinstance(make_llm(role="lead"), ChatGroq)
    assert isinstance(make_llm(role="worker"), ChatGroq)
    assert isinstance(make_llm(role="verifier"), ChatGroq)


def test_role_present_in_roles_block_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """When the named role is defined under `roles:`, that config wins
    over the top-level config."""
    _set_env(monkeypatch, GROQ_API_KEY="dummy", OLLAMA_API_KEY="dummy")
    yaml_path = _write_yaml(
        tmp_path,
        "provider: groq\n"
        "model: qwen/qwen3-32b\n"
        "roles:\n"
        "  worker:\n"
        "    provider: ollama\n"
        "    model: glm-5.1\n"
        "    api_key_env: OLLAMA_API_KEY\n",
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    # Top-level still wins for no-role + non-overridden roles.
    assert isinstance(make_llm(), ChatGroq)
    assert isinstance(make_llm(role="lead"), ChatGroq)
    # Worker has its own entry — uses ollama.
    assert isinstance(make_llm(role="worker"), ChatOllama)


def test_worker_falls_back_to_lead_when_only_lead_defined(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """`roles: { lead: {...} }` with no `worker` entry → worker uses
    lead's config (not the top-level)."""
    _set_env(monkeypatch, GROQ_API_KEY="dummy", GOOGLE_API_KEY="dummy")
    yaml_path = _write_yaml(
        tmp_path,
        "provider: groq\n"
        "model: qwen/qwen3-32b\n"
        "roles:\n"
        "  lead:\n"
        "    provider: google\n"
        "    model: gemma-4-31b-it\n",
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    # Worker / verifier inherit from lead.
    assert isinstance(make_llm(role="worker"), ChatGoogleGenerativeAI)
    assert isinstance(make_llm(role="verifier"), ChatGoogleGenerativeAI)
    # No-role still uses top-level.
    assert isinstance(make_llm(), ChatGroq)


def test_unknown_role_raises_value_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    _set_env(monkeypatch, GROQ_API_KEY="dummy")
    yaml_path = _write_yaml(tmp_path, "provider: groq\n")
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    with pytest.raises(ValueError, match="role="):
        make_llm(role="planner")  # type: ignore[arg-type]


def test_malformed_roles_entry_missing_provider_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """`roles.worker` without a `provider` field → factory error."""
    _set_env(monkeypatch, GROQ_API_KEY="dummy", OLLAMA_API_KEY="dummy")
    yaml_path = _write_yaml(
        tmp_path,
        "provider: groq\nroles:\n  worker:\n    model: glm-5.1\n",
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    with pytest.raises(LLMFactoryError, match="provider"):
        make_llm(role="worker")


def test_roles_block_must_be_a_mapping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """`roles:` written as a list instead of a mapping → factory error."""
    yaml_path = _write_yaml(
        tmp_path, "provider: groq\nroles:\n  - lead\n  - worker\n"
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    with pytest.raises(LLMFactoryError, match="mapping"):
        _read_yaml_config(role="worker")


def test_existing_callsites_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Sanity check that `make_llm()` with no argument still returns
    the top-level LLM — guards every existing caller (agent, eval
    harness, etc.) against silent behaviour change."""
    _set_env(monkeypatch, OLLAMA_API_KEY="dummy")
    yaml_path = _write_yaml(
        tmp_path,
        "provider: ollama\n"
        "model: glm-5.1\n"
        "api_key_env: OLLAMA_API_KEY\n"
        "# A roles block is allowed but has no effect on bare make_llm().\n"
        "roles:\n"
        "  worker:\n"
        "    provider: groq\n"
        "    model: qwen/qwen3-32b\n",
    )
    monkeypatch.setattr("nl_engine.llm.factory._CONFIG_PATH", yaml_path)
    # Bare call → ollama (top-level). Worker → groq (role override).
    assert isinstance(make_llm(), ChatOllama)
    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    assert isinstance(make_llm(role="worker"), ChatGroq)
