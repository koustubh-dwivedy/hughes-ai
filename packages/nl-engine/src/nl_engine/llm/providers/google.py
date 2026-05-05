"""Google AI Studio provider — Gemma 4 31B (open-weights, free tier).

Documented as the fallback provider in ADR-0004's amendment block.
Verified at HUG-196 implementation time:
  * `gemma-4-31b-it` is exposed at `models/gemma-4-31b-it` via the v1beta
    endpoint with `generateContent` + `countTokens` methods.
  * `langchain-google-genai`'s `ChatGoogleGenerativeAI.bind_tools()` works
    correctly with Gemma — `tool_calls` is populated in the standard
    LangChain shape (name, args, id).

Gemma 4 31B's response content is a structured list of blocks
(thinking + text). The thinking block leaks the model's reasoning, so
we strip it at the LangGraph layer where needed. Production agent code
already inspects `tool_calls` directly (not `content`), so this doesn't
affect tool-routing.
"""

from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = "gemma-4-31b-it"


class GoogleProviderError(RuntimeError):
    """Raised when the Google provider cannot be constructed."""


def make_google_llm(model: str | None = None) -> BaseChatModel:
    """Construct a `ChatGoogleGenerativeAI` instance against Google AI Studio.

    Raises `GoogleProviderError` if `GOOGLE_API_KEY` is not set.
    """
    if not os.environ.get("GOOGLE_API_KEY"):
        raise GoogleProviderError(
            "GOOGLE_API_KEY is not set; cannot construct the Google "
            "provider. Set the env var (Google AI Studio key) or switch "
            "LLM_PROVIDER to a different configured provider."
        )
    return ChatGoogleGenerativeAI(
        model=model or DEFAULT_MODEL,
        temperature=0,
    )
