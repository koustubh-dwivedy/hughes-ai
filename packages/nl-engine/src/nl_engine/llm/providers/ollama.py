"""Ollama Cloud provider — third option in the multi-provider family
(HUG-190 Phase E, 2026-05-06).

Currently configured for Ollama Cloud's hosted models (e.g.,
`qwen3-coder:480b`, `qwen3-vl:235b-instruct`, `glm-4.6`). The endpoint
also supports self-hosted Ollama via the `OLLAMA_BASE_URL` override.

Auth is via Bearer token (Ollama Cloud's standard) injected through
`client_kwargs`. `langchain-ollama`'s `ChatOllama` exposes the native
Ollama protocol at `/api/chat` which is what Ollama Cloud serves.
Tool-calling was verified at HUG-190 implementation time:
`qwen3-coder:480b` returns structured `tool_calls` arrays in the
LangChain-compatible shape.
"""

from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

DEFAULT_MODEL = "qwen3-coder:480b"
DEFAULT_BASE_URL = "https://ollama.com"

# HTTP timeout for every Ollama API call. Without an explicit timeout,
# `langchain-ollama → ollama-python → httpx` will block indefinitely if
# Ollama Cloud's GPU stalls or the connection drops without a clean
# reset (HUG-190 2026-05-07: observed a 24-min hang during eval).
# 120s is well above the longest legitimate inference observed
# (~90s on glm-5.1) and forces a clean TimeoutError that Phase C-bis
# retries cleanly on. Override via OLLAMA_TIMEOUT_S if needed.
DEFAULT_TIMEOUT_S = 120.0


class OllamaProviderError(RuntimeError):
    """Raised when the Ollama provider cannot be constructed."""


def make_ollama_llm(model: str | None = None) -> BaseChatModel:
    """Construct a `ChatOllama` instance against Ollama Cloud (or a
    self-hosted Ollama via `OLLAMA_BASE_URL`).

    Raises `OllamaProviderError` if `OLLAMA_API_KEY` is not set.
    """
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise OllamaProviderError(
            "OLLAMA_API_KEY is not set; cannot construct the Ollama "
            "provider. Set the env var or edit config/llm.yaml to point "
            "at a different provider."
        )
    base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
    timeout = float(os.environ.get("OLLAMA_TIMEOUT_S", DEFAULT_TIMEOUT_S))
    return ChatOllama(
        model=model or DEFAULT_MODEL,
        base_url=base_url,
        temperature=0,
        client_kwargs={
            "headers": {"Authorization": f"Bearer {api_key}"},
            "timeout": timeout,
        },
    )
