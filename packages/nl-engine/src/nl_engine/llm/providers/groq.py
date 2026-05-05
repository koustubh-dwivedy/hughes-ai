"""Groq provider — Qwen 3 32B per ADR-0004.

`reasoning_format="hidden"` is non-negotiable per ADR-0004 — without it
Qwen 3's chain-of-thought leaks into tool-call JSON and breaks parsing.
"""

from __future__ import annotations

import os
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq

DEFAULT_MODEL = "qwen/qwen3-32b"
_REASONING_FORMAT: Literal["hidden"] = "hidden"


class GroqProviderError(RuntimeError):
    """Raised when the Groq provider cannot be constructed."""


def make_groq_llm(model: str | None = None) -> BaseChatModel:
    """Construct a Groq `ChatGroq` instance with ADR-0004 invariants.

    Raises `GroqProviderError` if `GROQ_API_KEY` is not set.
    """
    if not os.environ.get("GROQ_API_KEY"):
        raise GroqProviderError(
            "GROQ_API_KEY is not set; cannot construct the Groq provider. "
            "Either set the env var or switch LLM_PROVIDER to a different "
            "configured provider."
        )
    return ChatGroq(
        model=model or DEFAULT_MODEL,
        temperature=0,
        reasoning_format=_REASONING_FORMAT,
    )
