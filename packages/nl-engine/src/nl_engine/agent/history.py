"""Helpers for shaping the agent's message history before each LLM call.

`_ensure_system_prompt` prepends the OpenUI system prompt without writing
it into checkpointed state. `_truncate_history` enforces a token budget
so very long threads don't crash on context-overflow.
"""

from __future__ import annotations

import logging

from langchain_core.messages import BaseMessage, SystemMessage

from nl_engine.agent.system_prompt import SYSTEM_PROMPT as _OPENUI_SYSTEM_PROMPT

log = logging.getLogger(__name__)

# Both Qwen 3 32B and Gemma 4 31B have 128K-131K context windows; trim
# at 100K to leave headroom for the system prompt + tool descs + reply.
# Heuristic: ~4 chars per token.
_TOKEN_BUDGET = 100_000
_CHARS_PER_TOKEN_HEURISTIC = 4


def ensure_system_prompt(messages: list[BaseMessage]) -> list[BaseMessage]:
    if messages and isinstance(messages[0], SystemMessage):
        return messages
    return [SystemMessage(content=_OPENUI_SYSTEM_PROMPT), *messages]


def _estimate_tokens(messages: list[BaseMessage]) -> int:
    total = 0
    for msg in messages:
        c = msg.content
        total += len(c) if isinstance(c, str) else len(str(c))
    return total // _CHARS_PER_TOKEN_HEURISTIC


def truncate_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Drop oldest non-system messages until under token budget."""
    if _estimate_tokens(messages) <= _TOKEN_BUDGET:
        return messages
    system: list[BaseMessage] = []
    rest: list[BaseMessage] = []
    for msg in messages:
        (system if isinstance(msg, SystemMessage) else rest).append(msg)
    dropped = 0
    while rest and _estimate_tokens(system + rest) > _TOKEN_BUDGET:
        rest.pop(0)
        dropped += 1
    if dropped:
        log.warning(
            "agent history truncated: dropped %d oldest messages "
            "to fit %d-token budget",
            dropped,
            _TOKEN_BUDGET,
        )
    return system + rest
