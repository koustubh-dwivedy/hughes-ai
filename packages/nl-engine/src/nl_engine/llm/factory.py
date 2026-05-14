"""LLM factory — config-file driven, single LLM only (no fallback).

Resolution order (HUG-190, 2026-05-06):

1. If `config/llm.yaml` exists at the repo root, read provider/model/
   api_key_env from there.
2. Otherwise (or for tests passing an explicit `LLMConfig`), fall back
   to env vars (`LLM_PROVIDER`, `LLM_MODEL`).

There is no fallback chain. One provider, one model, one code path.
If a provider goes down, ops swaps the YAML file — we don't rely on
hidden multi-provider mixing (per user directive 2026-05-06).

HUG-204 extension: `make_llm` accepts an optional `role` argument
(`lead | worker | verifier`) for the deep-research feature. When the
YAML has an optional `roles:` block AND the named role is defined,
the role-specific config is used. Otherwise the top-level config
applies (full back-compat — existing `make_llm()` callers are
unchanged). ADR-0004's single-LLM rule still defaults; per-role
overrides are opt-in via the `roles:` block.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from langchain_core.language_models import BaseChatModel

from nl_engine.llm.providers.google import make_google_llm
from nl_engine.llm.providers.groq import make_groq_llm
from nl_engine.llm.providers.ollama import make_ollama_llm
from nl_engine.llm.providers.openai_compatible import (
    make_openai_compatible_llm,
)
from nl_engine.logging import get_logger

ProviderName = Literal["groq", "google", "ollama", "openai_compatible"]
Role = Literal["lead", "worker", "verifier"]

_VALID_PROVIDERS: frozenset[str] = frozenset(
    {"groq", "google", "ollama", "openai_compatible"}
)
_VALID_ROLES: frozenset[str] = frozenset({"lead", "worker", "verifier"})

_DEFAULT_PROVIDER: ProviderName = "groq"

# `config/llm.yaml` lives at the repo root. Resolved relative to this
# file: packages/nl-engine/src/nl_engine/llm/factory.py → up 5 = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONFIG_PATH = _REPO_ROOT / "config" / "llm.yaml"

_log = get_logger().bind(component="llm.factory")


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


def _config_from_dict(raw: dict[str, Any], source: str) -> LLMConfig:
    """Build an `LLMConfig` from a dict — used both by the top-level
    config read and by per-role lookups under the `roles:` block.
    Raises `LLMFactoryError` on malformed input."""
    provider_raw = raw.get("provider", "")
    if not provider_raw:
        raise LLMFactoryError(f"{source} is missing required 'provider' field")
    provider = _validate_provider(provider_raw, source=source)
    return LLMConfig(
        provider=provider,
        model=raw.get("model"),
        api_key_env=raw.get("api_key_env") or "OPENAI_API_KEY",
        base_url_env=raw.get("base_url_env") or "OPENAI_BASE_URL",
    )


def _read_yaml_config(role: Role | None = None) -> LLMConfig | None:
    """Return a config from `config/llm.yaml`, or None if absent.

    When `role` is provided AND the yaml has a `roles:` block with that
    role, the role-specific config wins. Otherwise (`role` is None, or
    the `roles:` block is missing, or the named role isn't in the
    block), the top-level config is used — preserving the ADR-0004
    single-LLM default. Lookup order for a given role:
      1. `roles.<role>` if present.
      2. `roles.lead` if present (workers/verifier inherit from lead).
      3. Top-level config.

    Side-effect: providers read their canonical env vars at construction
    time; the YAML's `api_key_env` is informational + lets ops use a
    custom name without changing code.
    """
    if not _CONFIG_PATH.exists():
        return None
    raw = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if role is not None:
        roles_block = raw.get("roles") or {}
        if not isinstance(roles_block, dict):
            raise LLMFactoryError(
                "config/llm.yaml 'roles:' must be a mapping of role-name → config"
            )
        if role in roles_block:
            return _config_from_dict(
                roles_block[role], source=f"config/llm.yaml roles.{role}"
            )
        if "lead" in roles_block and role != "lead":
            # Workers/verifier inherit from lead when explicitly absent.
            return _config_from_dict(
                roles_block["lead"], source="config/llm.yaml roles.lead"
            )
        # Fall through to top-level — no role-specific override.
    return _config_from_dict(raw, source="config/llm.yaml")


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


def _resolve_config(role: Role | None = None) -> LLMConfig:
    """Read `config/llm.yaml` first (with optional role override), then
    env vars. Tests can pass an explicit `LLMConfig` to `make_llm()`
    to bypass both."""
    yaml_cfg = _read_yaml_config(role=role)
    if yaml_cfg is not None:
        return yaml_cfg
    return _read_env_config()


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


def make_llm(
    config: LLMConfig | None = None,
    *,
    role: Role | None = None,
) -> BaseChatModel:
    """Construct an LLM (single provider, no fallback wrapper).

    `config` overrides resolution; pass it from tests to avoid touching
    files or env vars. In production, call with no argument and let
    `config/llm.yaml` (or env-var fallback) drive the construction.

    `role` (HUG-204) selects a role-specific LLM when `config/llm.yaml`
    has a `roles:` block defining one. Valid values: `"lead"`,
    `"worker"`, `"verifier"`. When the block is absent or the named
    role isn't present, the top-level config is used — preserving
    today's single-LLM behaviour (ADR-0004 default). Passing `role`
    is opt-in; existing callers calling `make_llm()` keep working
    unchanged.

    Raises `ValueError` for an unknown role string.
    """
    if role is not None and role not in _VALID_ROLES:
        raise ValueError(
            f"make_llm role={role!r} is not valid; "
            f"allowed: {sorted(_VALID_ROLES)}"
        )
    cfg = config or _resolve_config(role=role)
    _log.info(
        "llm.factory.dispatched",
        role=role,
        provider=cfg.provider,
        model=cfg.model,
    )
    return _construct(cfg)
