"""LLM factory — config-file driven, single LLM only (no fallback).

Resolution order (HUG-190, 2026-05-06):

1. If `config/llm.yaml` exists at the repo root, read provider/model/
   api_key_env from there.
2. Otherwise (or for tests passing an explicit `LLMConfig`), fall back
   to env vars (`LLM_PROVIDER`, `LLM_MODEL`).

There is no fallback chain. One provider, one model, one code path.
If a provider goes down, ops swaps the YAML file — we don't rely on
hidden multi-provider mixing (per user directive 2026-05-06).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from langchain_core.language_models import BaseChatModel

from nl_engine.llm.providers.google import make_google_llm
from nl_engine.llm.providers.groq import make_groq_llm
from nl_engine.llm.providers.ollama import make_ollama_llm
from nl_engine.llm.providers.openai_compatible import (
    make_openai_compatible_llm,
)

ProviderName = Literal["groq", "google", "ollama", "openai_compatible"]

_VALID_PROVIDERS: frozenset[str] = frozenset(
    {"groq", "google", "ollama", "openai_compatible"}
)

_DEFAULT_PROVIDER: ProviderName = "groq"

# `config/llm.yaml` lives at the repo root. Resolved relative to this
# file: packages/nl-engine/src/nl_engine/llm/factory.py → up 5 = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONFIG_PATH = _REPO_ROOT / "config" / "llm.yaml"


@dataclass(frozen=True)
class LLMConfig:
    """Resolved LLM configuration. Single provider; no fallback."""

    provider: ProviderName
    model: str | None = None  # passes through to the provider; None = default
    # HUG-206: env-var NAMES used by the openai_compatible provider to
    # resolve credentials + endpoint at construction time. Ignored by
    # other providers, which read their own canonical env vars
    # (GROQ_API_KEY, GOOGLE_API_KEY, OLLAMA_API_KEY).
    api_key_env: str = "OPENAI_API_KEY"
    base_url_env: str = "OPENAI_BASE_URL"


class LLMFactoryError(RuntimeError):
    """Raised on invalid configuration."""


def _validate_provider(name: str, source: str) -> ProviderName:
    """Narrow a string into the `ProviderName` literal or raise."""
    lowered = name.strip().lower()
    if lowered not in _VALID_PROVIDERS:
        raise LLMFactoryError(
            f"{source} provider={lowered!r} is not valid; "
            f"allowed: {sorted(_VALID_PROVIDERS)}"
        )
    return lowered  # type: ignore[return-value]


def _read_yaml_config() -> LLMConfig | None:
    """Return a config from `config/llm.yaml`, or None if absent.

    Side-effect: sets `os.environ` with the api_key_env var's resolved
    name as a hint to providers (they still read their canonical env
    vars; the YAML's `api_key_env` is informational + lets ops use a
    custom name without changing code).
    """
    if not _CONFIG_PATH.exists():
        return None
    raw = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    provider = _validate_provider(raw.get("provider", ""), source="config/llm.yaml")
    model = raw.get("model")
    return LLMConfig(
        provider=provider,
        model=model,
        api_key_env=raw.get("api_key_env") or "OPENAI_API_KEY",
        base_url_env=raw.get("base_url_env") or "OPENAI_BASE_URL",
    )


def _read_env_config() -> LLMConfig:
    """Fallback config resolution from env vars. Used for tests and as
    a backup if `config/llm.yaml` is absent."""
    raw = os.environ.get("LLM_PROVIDER", "").strip().lower()
    provider: ProviderName
    if not raw:
        provider = _DEFAULT_PROVIDER
    else:
        provider = _validate_provider(raw, source="LLM_PROVIDER")
    model = os.environ.get("LLM_MODEL", "").strip() or None
    return LLMConfig(provider=provider, model=model)


def _resolve_config() -> LLMConfig:
    """Read `config/llm.yaml` first, then env vars. Tests can pass an
    explicit LLMConfig to `make_llm()` to bypass both."""
    return _read_yaml_config() or _read_env_config()


def _construct(cfg: LLMConfig) -> BaseChatModel:
    if cfg.provider == "groq":
        return make_groq_llm(cfg.model)
    if cfg.provider == "google":
        return make_google_llm(cfg.model)
    if cfg.provider == "openai_compatible":
        return make_openai_compatible_llm(
            cfg.model,
            api_key_env=cfg.api_key_env,
            base_url_env=cfg.base_url_env,
        )
    return make_ollama_llm(cfg.model)


def make_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """Construct the agent LLM (single provider, no fallback wrapper).

    `config` overrides resolution; pass it from tests to avoid touching
    files or env vars. In production, call with no argument and let
    `config/llm.yaml` (or env-var fallback) drive the construction.
    """
    cfg = config or _resolve_config()
    return _construct(cfg)
