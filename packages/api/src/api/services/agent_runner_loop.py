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
    finalization path in `stream_user_turn`.

    `initial_history_len` is the length of the AgentState's `messages`
    list at turn start (history rehydrated from the DB + the new user
    message). LangGraph `stream_mode="values"` yields the entire state
    on each step, so without this offset we'd re-persist every prior
    turn's AI/Tool messages on every follow-up turn. See HUG / fix:
    consume_queue slices `messages[initial_history_len:]`.
    """

    __slots__ = (
        "seen",
        "step_idx",
        "trace",
        "token_count",
        "token_chars",
        "initial_history_len",
    )

    def __init__(self, initial_history_len: int = 0) -> None:
        self.seen: set[int] = set()
        self.step_idx = 0
        self.trace: list[dict[str, Any]] = []
        self.token_count = 0
        self.token_chars = 0
        self.initial_history_len = initial_history_len


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
        # Slice off the initial-history prefix so prior turns' messages
        # (rehydrated from the DB at turn start) aren't treated as new
        # output of this turn. Without this, every follow-up turn would
        # re-persist every prior AI/Tool message and the chat would
        # accumulate duplicate answers (issue 2 root cause).
        all_msgs = chunk.get("messages", [])
        for msg in all_msgs[state.initial_history_len :]:
            if id(msg) in state.seen or isinstance(msg, HumanMessage):
                state.seen.add(id(msg))
                continue
            state.seen.add(id(msg))
            state.step_idx += 1
            for event in process_message(
                msg, state.step_idx, thread_id, db_url, state.trace
            ):
                yield event
