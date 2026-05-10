"""Generic provider for any OpenAI-wire-compatible inference endpoint
(HUG-206).

The OpenAI HTTP protocol — POST /v1/chat/completions with a JSON body
that has `messages`, `tools`, `tool_choice`, `stream` — has become the
de-facto industry standard. Cerebras, Together, Anyscale, Fireworks,
vLLM, llama.cpp, and OpenAI itself all serve it. Any model hosted
behind such an endpoint can be reached through `langchain-openai`'s
`ChatOpenAI` regardless of the model's underlying architecture.

Adding a new OpenAI-compatible endpoint is a config-file change,
not a code change. `config/llm.yaml`:

    provider: openai_compatible
    model: <whatever the endpoint accepts>
    api_key_env: <env var holding the bearer token>
    base_url_env: <env var holding the endpoint URL, optional>

Both the API key and base URL are read from environment variables
named in the YAML (so the YAML stays free of secrets and ops can
override either without code changes). The defaults below match the
Cerebras Inference API; override `base_url_env` for any other
endpoint (Together, Fireworks, OpenAI itself, etc.)
"""

from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

# Cerebras's hosted inference endpoint — sensible default since they
# were the first non-OpenAI use case for this provider. Override via
# `base_url_env` in config/llm.yaml for any other endpoint.
DEFAULT_BASE_URL = "https://api.cerebras.ai/v1"

# HTTP timeout per call. Mirrors `ollama.py`'s 120s budget — well above
# observed legitimate inference times (~90s on slower hosted models),
# fast enough that a true provider hang surfaces as a clean timeout
# the agent's transient-retry layer can recover from.
DEFAULT_TIMEOUT_S = 120.0


class OpenAICompatibleProviderError(RuntimeError):
    """Raised when the openai_compatible provider cannot be constructed
    (missing API key, malformed base URL, etc.)."""


def make_openai_compatible_llm(
    model: str | None = None,
    *,
    api_key_env: str = "OPENAI_API_KEY",
    base_url_env: str = "OPENAI_BASE_URL",
) -> BaseChatModel:
    """Construct a `ChatOpenAI` client pointed at any OpenAI-wire-
    compatible endpoint.

    `api_key_env` and `base_url_env` are the NAMES of the environment
    variables to read — not the values. This indirection lets ops use
    a custom env var name (e.g. `CEREBRAS_API_KEY`) without changing
    the provider code; the YAML's `api_key_env` field passes through.

    Raises `OpenAICompatibleProviderError` if the key isn't set in the
    environment.
    """
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise OpenAICompatibleProviderError(
            f"{api_key_env} is not set; cannot construct the openai_compatible "
            "provider. Either set the env var or edit config/llm.yaml."
        )
    base_url = os.environ.get(base_url_env) or DEFAULT_BASE_URL
    timeout = float(os.environ.get("OPENAI_COMPAT_TIMEOUT_S", DEFAULT_TIMEOUT_S))
    if model is None:
        # No sensible default for a model — providers serve different
        # catalogs. Force the YAML to be explicit.
        raise OpenAICompatibleProviderError(
            "openai_compatible provider requires `model` in config/llm.yaml"
        )
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0,
        timeout=timeout,
    )
