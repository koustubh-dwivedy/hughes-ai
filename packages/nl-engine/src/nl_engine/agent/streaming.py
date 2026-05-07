"""Per-request token-sink registry for streaming LLM output across the
graph → runner boundary (HUG-202 Phase 2).

The agent_step (inside the LangGraph node) needs to forward token
deltas of the `final_answer.summary` arg to the SSE consumer, but
nl_engine cannot import api. We use a process-local registry keyed on
request_id: the runner registers a sink at turn start, the agent_step
looks it up by `state.request_id` while streaming, and the runner
clears it when the turn ends.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from threading import Lock

# Sink callable accepts a single string delta. Implementations are
# expected to be cheap + non-blocking (e.g. push onto an asyncio queue
# via loop.call_soon_threadsafe). Exceptions are swallowed to keep the
# LLM call alive.
TokenSink = Callable[[str], None]

_sinks: dict[str, TokenSink] = {}
_lock = Lock()


def set_token_sink(request_id: str, sink: TokenSink) -> None:
    """Register `sink` for the given request_id. No-op for empty ids."""
    if not request_id:
        return
    with _lock:
        _sinks[request_id] = sink


def clear_token_sink(request_id: str) -> None:
    """Remove any sink for the given request_id. Idempotent."""
    if not request_id:
        return
    with _lock:
        _sinks.pop(request_id, None)


def emit_token(request_id: str, content_delta: str) -> None:
    """Forward a content delta to the registered sink, if any.

    Empty deltas / unknown request_ids are no-ops. Sink exceptions are
    swallowed — the streaming LLM call must never crash because the SSE
    consumer is unreachable."""
    if not request_id or not content_delta:
        return
    with _lock:
        sink = _sinks.get(request_id)
    if sink is None:
        return
    # Never let sink errors abort the LLM call — the streaming consumer
    # being unreachable shouldn't fail the agent turn.
    with contextlib.suppress(Exception):
        sink(content_delta)
