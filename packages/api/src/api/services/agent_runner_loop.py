"""SSE event-loop driver for stream_user_turn (HUG-202 Phase 4).

Pulled out of agent_runner.py so the runner module fits the 300-line
structural cap. Owns the per-turn mutable state + the consume-the-
queue async generator.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage


class TurnState:
    """Per-turn mutable state shared between the consume loop and the
    finalization path in `stream_user_turn`."""

    __slots__ = ("seen", "step_idx", "trace", "token_count", "token_chars")

    def __init__(self) -> None:
        self.seen: set[int] = set()
        self.step_idx = 0
        self.trace: list[dict[str, Any]] = []
        self.token_count = 0
        self.token_chars = 0


async def consume_queue(
    queue: Any,
    state: TurnState,
    thread_id: UUID,
    db_url: str,
    *,
    is_error_sentinel: Callable[[Any], bool],
    error_frame: Callable[[str], dict[str, Any]],
    token_sentinel_key: str,
    token_frame: Callable[[str], dict[str, Any]],
    process_message: Callable[
        [Any, int, UUID, str, list[dict[str, Any]]],
        list[dict[str, Any]],
    ],
) -> AsyncIterator[dict[str, Any]]:
    """Drain `queue` of LangGraph state chunks + token sentinels +
    error sentinels, translating each into the SSE event dict the
    sse_starlette layer expects."""
    while True:
        chunk = await queue.get()
        if chunk is None:
            return
        if is_error_sentinel(chunk):
            yield error_frame(chunk.message)
            continue
        if isinstance(chunk, dict) and token_sentinel_key in chunk:
            delta = chunk[token_sentinel_key]
            state.token_count += 1
            state.token_chars += len(delta)
            yield token_frame(delta)
            continue
        for msg in chunk.get("messages", []):
            if id(msg) in state.seen or isinstance(msg, HumanMessage):
                state.seen.add(id(msg))
                continue
            state.seen.add(id(msg))
            state.step_idx += 1
            for event in process_message(
                msg, state.step_idx, thread_id, db_url, state.trace
            ):
                yield event
