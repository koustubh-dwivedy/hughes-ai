"""Live-API smoke tests for both LLM providers (HUG-196).

Skipped when the corresponding API key is not set. Not part of the
default CI run — opt-in only.
"""

from __future__ import annotations

import os

import pytest
from langchain_core.messages import HumanMessage
from nl_engine.llm import LLMConfig, make_llm


@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set",
)
def test_groq_provider_smoke() -> None:
    llm = make_llm(LLMConfig(provider="groq"))
    resp = llm.invoke([HumanMessage(content="Reply with the single word: pong")])
    assert resp.content


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
def test_google_provider_smoke() -> None:
    llm = make_llm(LLMConfig(provider="google"))
    resp = llm.invoke([HumanMessage(content="Reply with the single word: pong")])
    # Gemma's response.content is a list of blocks (thinking + text);
    # str-cast for the simple assertion.
    assert resp.content
