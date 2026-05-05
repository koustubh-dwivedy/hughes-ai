"""Single source of truth for the agent's LLM instance.

Per ADR-0004, the agent runs on Qwen 3 32B via Groq Cloud. We use
`langchain_groq.ChatGroq` directly — `bind_tools()` is native, the
message-conversion bookkeeping is handled, and `BaseChatModel` is
LangChain's stable interface that LangGraph expects.

`reasoning_format="hidden"` is mandatory: without it, Qwen 3's
chain-of-thought leaks into tool-call JSON and breaks the parser.
The kwarg is pinned in `make_agent_llm()`; the `routes/threads.py`
factory pulls from here so test injection points (`app.state.agent_llm`)
remain the only override surface.
"""

from __future__ import annotations

from typing import Literal

from langchain_groq import ChatGroq

# Pinned by ADR-0004. Do not parameterize — a per-call override would
# defeat the reasoning-format invariant.
_MODEL = "qwen/qwen3-32b"
_REASONING_FORMAT: Literal["hidden"] = "hidden"


def make_agent_llm() -> ChatGroq:
    """Construct the production agent LLM.

    `reasoning_format` is a first-class kwarg on ChatGroq (not wrapped
    in `model_kwargs`); langchain-groq enforces this — model_kwargs
    bouncing it back fails with a ValidationError. Tests bypass this
    via `app.state.agent_llm` (see `routes/threads.py::_get_llm`).
    """
    return ChatGroq(
        model=_MODEL,
        temperature=0,
        reasoning_format=_REASONING_FORMAT,
    )
