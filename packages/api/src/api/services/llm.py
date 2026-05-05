"""Single source of truth for the agent's LLM instance.

This module is now a thin re-export of `nl_engine.llm.make_llm` (HUG-196).
The factory reads `LLM_PROVIDER` / `LLM_FALLBACK_PROVIDER` env vars and
constructs the right provider with ADR-0004's invariants enforced inside
`nl_engine.llm.providers.groq`. Default provider is groq.

Tests bypass this via `app.state.agent_llm` (see `routes/threads.py::_get_llm`).
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from nl_engine.llm import make_llm


def make_agent_llm() -> BaseChatModel:
    """Construct the production agent LLM via `nl_engine.llm.make_llm`."""
    return make_llm()
