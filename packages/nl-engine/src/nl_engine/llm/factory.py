"""LLM factory — env-var dispatcher + optional fallback chain wiring."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from langchain_core.language_models import BaseChatModel

from nl_engine.llm.fallback import FallbackChatModel
from nl_engine.llm.providers.google import make_google_llm
from nl_engine.llm.providers.groq import make_groq_llm

ProviderName = Literal["groq", "google"]

_VALID_PROVIDERS: frozenset[str] = frozenset({"groq", "google"})

_DEFAULT_PROVIDER: ProviderName = "groq"


@dataclass(frozen=True)
class LLMConfig:
    """Resolved LLM configuration derived from env vars."""

    provider: ProviderName
    fallback_provider: ProviderName | None = None
    model: str | None = None  # passes through to the provider; None = default


class LLMFactoryError(RuntimeError):
    """Raised on invalid configuration."""


def _read_provider(env_var: str, default: ProviderName | None) -> ProviderName | None:
    raw = os.environ.get(env_var, "").strip().lower()
    if not raw:
        return default
    if raw not in _VALID_PROVIDERS:
        raise LLMFactoryError(
            f"{env_var}={raw!r} is not a valid provider; "
            f"allowed: {sorted(_VALID_PROVIDERS)}"
        )
    # Type narrowed by the membership check above; cast is safe.
    return raw  # type: ignore[return-value]


def _resolve_config() -> LLMConfig:
    primary = _read_provider("LLM_PROVIDER", _DEFAULT_PROVIDER) or _DEFAULT_PROVIDER
    fallback = _read_provider("LLM_FALLBACK_PROVIDER", None)
    if fallback == primary:
        raise LLMFactoryError(
            f"LLM_FALLBACK_PROVIDER must differ from LLM_PROVIDER "
            f"(both are {primary!r}); fallback chain would be a no-op."
        )
    model = os.environ.get("LLM_MODEL", "").strip() or None
    return LLMConfig(provider=primary, fallback_provider=fallback, model=model)


def _construct(provider: ProviderName, model: str | None) -> BaseChatModel:
    if provider == "groq":
        return make_groq_llm(model)
    return make_google_llm(model)


def make_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """Construct the agent LLM.

    `config` overrides env-var resolution; pass it from tests to avoid
    polluting `os.environ`. In production code, call with no argument
    and let env vars drive the construction.
    """
    cfg = config or _resolve_config()
    primary = _construct(cfg.provider, cfg.model)
    if cfg.fallback_provider is None:
        return primary
    fallback = _construct(cfg.fallback_provider, None)  # fallback uses its own default
    return FallbackChatModel(primary=primary, fallback=fallback)
