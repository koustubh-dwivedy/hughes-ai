"""Tests for the per-turn consume_queue dedup logic.

Issue 2 regression guard: prior-history messages get rehydrated from
the DB into fresh Python objects at the start of every follow-up turn
(see `_build_initial_state` → `from_canonical`). LangGraph's
`stream_mode="values"` then yields the ENTIRE state on each step,
including those rehydrated history messages. Before the fix, the
`state.seen` id()-based dedup couldn't recognize them as historical
and the runner re-persisted them — causing Q1's final_answer DSL to
show up under Q2 in the UI ("the chart of not just the second
question but also the first").

The fix slices off the initial-history prefix in `consume_queue` via
`state.initial_history_len`. These tests verify both the slicing and
that the existing in-turn dedup still works.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest
from api.services.agent_runner_loop import TurnState, consume_queue
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def _build_calls(
    *, initial_history_len: int, chunks: list[Any]
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Drive consume_queue with the given queue contents + history
    offset and capture (processed_msgs, emitted_events).

    Returns the messages process_message was invoked on (in order),
    and the events consume_queue yielded.
    """
    processed: list[Any] = []

    def fake_process(
        msg: Any, _step_idx: int, _thread_id: UUID, _db_url: str,
        _trace: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        processed.append(msg)
        return [{"event": "step", "data": "stub"}]

    queue: asyncio.Queue[Any] = asyncio.Queue()
    for c in chunks:
        queue.put_nowait(c)
    queue.put_nowait(None)
    state = TurnState()
    state.initial_history_len = initial_history_len

    async def _drive() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        async for ev in consume_queue(
            queue,
            state,
            uuid4(),
            "fake-db",
            is_error_sentinel=lambda _c: False,
            error_frame=lambda m: {"event": "error", "data": m},
            token_sentinel_key="_token_delta",  # noqa: S106 — keyword, not a secret
            token_frame=lambda d: {"event": "token", "data": d},
            process_message=fake_process,
        ):
            out.append(ev)
        return out

    return processed, asyncio.run(_drive())


def test_consume_queue_skips_prior_history_messages() -> None:
    """The smoking-gun case: a follow-up turn where the first chunk
    yielded by the graph contains 3 prior messages + 1 new user msg +
    1 new AI message. Only the new AI should be processed."""
    prior_human = HumanMessage(content="Q1")
    prior_ai = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "final_answer",
                "args": {"summary": "Q1 answer"},
                "id": "c1",
            }
        ],
    )
    prior_tool = ToolMessage(
        content='{"summary":"Q1 answer"}', name="final_answer", tool_call_id="c1"
    )
    new_human = HumanMessage(content="Q2")
    new_ai = AIMessage(
        content="",
        tool_calls=[{"name": "list_metrics", "args": {}, "id": "c2"}],
    )
    initial_history_len = 4  # prior_human, prior_ai, prior_tool, new_human

    chunk1 = {
        "messages": [prior_human, prior_ai, prior_tool, new_human, new_ai],
    }
    processed, events = _build_calls(
        initial_history_len=initial_history_len, chunks=[chunk1]
    )

    # Only the new AI message should have been handed to process_message.
    # Pre-fix this list would be [prior_ai, prior_tool, new_ai] = 3 items.
    assert len(processed) == 1, (
        f"expected exactly 1 processed message (the new AI), got {len(processed)}: "
        f"{[type(m).__name__ for m in processed]}"
    )
    assert processed[0] is new_ai
    assert len(events) == 1


def test_consume_queue_processes_new_messages_only_once_across_chunks() -> None:
    """LangGraph re-yields the same Python objects across successive
    chunks (a node-step adds one new message; subsequent chunks include
    prior new messages + the latest one). The existing id() dedup in
    state.seen must still skip already-processed messages WITHIN the
    turn, while initial_history_len skips the rehydrated history."""
    new_ai_1 = AIMessage(
        content="",
        tool_calls=[{"name": "list_metrics", "args": {}, "id": "c1"}],
    )
    new_tool_1 = ToolMessage(
        content="{}", name="list_metrics", tool_call_id="c1"
    )
    new_ai_2 = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "final_answer",
                "args": {"summary": "ok"},
                "id": "c2",
            }
        ],
    )

    chunks: list[Any] = [
        {"messages": [new_ai_1]},
        {"messages": [new_ai_1, new_tool_1]},
        {"messages": [new_ai_1, new_tool_1, new_ai_2]},
    ]
    processed, _ = _build_calls(initial_history_len=0, chunks=chunks)
    # Each new message should be processed exactly once even though it
    # appears in multiple chunks.
    assert processed == [new_ai_1, new_tool_1, new_ai_2]


def test_consume_queue_skips_user_human_messages_in_new_section() -> None:
    """HumanMessages are always skipped, even in the post-history slice
    — they're already persisted at turn-start (append_message)."""
    new_human = HumanMessage(content="Q2")
    new_ai = AIMessage(
        content="",
        tool_calls=[{"name": "list_metrics", "args": {}, "id": "c1"}],
    )
    chunk = {"messages": [new_human, new_ai]}
    processed, _ = _build_calls(initial_history_len=0, chunks=[chunk])
    assert processed == [new_ai]


@pytest.mark.parametrize("history_len", [0, 1, 5, 12])
def test_consume_queue_handles_empty_new_section(history_len: int) -> None:
    """When the chunk is fully consumed by history, nothing processes."""
    msgs = [HumanMessage(content=f"m{i}") for i in range(history_len)]
    chunk = {"messages": msgs}
    processed, _ = _build_calls(initial_history_len=history_len, chunks=[chunk])
    assert processed == []
