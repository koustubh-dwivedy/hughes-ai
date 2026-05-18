"""HUG-265 — chat_process_message must close every turn with `event: final`.

Regression test for the silent dead-end in the agent graph state machine:
when the LLM responds with prose and no tool_calls (e.g. "Hello" →
"Hi! How can I help?"), graph._route returns END without producing a
`final_answer` ToolMessage. The previous chat_process_message emitted
no terminal event in that case, leaving the SSE consumer to never fire
`streamFinal` and the UI to lock indefinitely.

This file asserts that AIMessages with empty `tool_calls` now produce
an `event: final` payload anchored on the persisted assistant row.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from api.services.agent_runner_chat import chat_process_message
from api.types.threads import ThreadMessage
from langchain_core.messages import AIMessage, ToolMessage


def _persisted_assistant_stub(content: str = "Hello! How can I help?") -> ThreadMessage:
    """Mirror what persist_assistant returns for an AIMessage row."""
    return ThreadMessage(
        message_id=uuid4(),
        thread_id=uuid4(),
        role="assistant",
        content=content,
        tool_calls=None,
        created_at=datetime.now(UTC),
    )


def test_prose_aimessage_emits_synthetic_final() -> None:
    """An AIMessage with empty tool_calls (terminal prose) must produce
    an `event: final` payload pointing at the persisted assistant row."""
    persisted = _persisted_assistant_stub("Hi there!")
    msg = AIMessage(content="Hi there!")

    with patch(
        "api.services.agent_runner_chat.persist_assistant",
        return_value=persisted,
    ):
        events = chat_process_message(
            msg=msg,
            step_idx=1,
            thread_id=uuid4(),
            db_url="postgresql://stub",
            trace=[],
        )

    final_events = [e for e in events if e["event"] == "final"]
    assert len(final_events) == 1, (
        f"expected exactly one event:final, got {len(final_events)} "
        f"(all events: {[e['event'] for e in events]})"
    )
    data = json.loads(final_events[0]["data"])
    assert data["openui"] is None
    assert data["message"]["message_id"] == str(persisted.message_id)
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "Hi there!"


def test_intermediate_aimessage_with_tool_calls_does_not_emit_final() -> None:
    """An AIMessage that fires a tool call is intermediate — the graph
    will continue to the tool node. Must NOT emit a synthetic final."""
    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "list_metrics", "args": {}, "id": "call_abc"}
        ],
    )

    with patch(
        "api.services.agent_runner_chat.persist_assistant",
        return_value=_persisted_assistant_stub(""),
    ):
        events = chat_process_message(
            msg=msg,
            step_idx=1,
            thread_id=uuid4(),
            db_url="postgresql://stub",
            trace=[],
        )

    final_events = [e for e in events if e["event"] == "final"]
    assert final_events == [], (
        f"intermediate AIMessage should not emit final, "
        f"got {final_events}"
    )


def test_final_answer_toolmessage_still_emits_final() -> None:
    """Backward compatibility: the canonical final_answer ToolMessage
    path must continue to emit `event: final` (this is what shipped
    before HUG-265 and the deep-research flow depends on it)."""
    tid = uuid4()
    persisted_tool = ThreadMessage(
        message_id=uuid4(),
        thread_id=tid,
        role="tool",
        content='{"summary": "ok", "rows": []}',
        tool_calls=None,
        openui_dsl=None,
        created_at=datetime.now(UTC),
    )
    msg = ToolMessage(
        content='{"summary": "ok", "rows": []}',
        name="final_answer",
        tool_call_id="call_xyz",
    )

    with patch(
        "api.services.agent_runner_chat.persist_tool",
        return_value=persisted_tool,
    ):
        events = chat_process_message(
            msg=msg,
            step_idx=2,
            thread_id=tid,
            db_url="postgresql://stub",
            trace=[],
        )

    final_events = [e for e in events if e["event"] == "final"]
    assert len(final_events) == 1


def test_step_cap_aimessage_also_emits_final() -> None:
    """Happy side-benefit: graph._step_cap_node appends an AIMessage
    with tool_calls=[] when the agent hits its step cap. HUG-265's
    synthesizer catches that same shape, so step-cap turns now also
    close cleanly instead of stranding the UI."""
    step_cap_msg = AIMessage(
        content=(
            "I couldn't reach an answer within the 20-step limit for "
            "this turn. Try rephrasing or breaking the question into "
            "smaller parts."
        ),
    )

    with patch(
        "api.services.agent_runner_chat.persist_assistant",
        return_value=_persisted_assistant_stub(step_cap_msg.content),
    ):
        events = chat_process_message(
            msg=step_cap_msg,
            step_idx=20,
            thread_id=uuid4(),
            db_url="postgresql://stub",
            trace=[],
        )

    final_events = [e for e in events if e["event"] == "final"]
    assert len(final_events) == 1
    data = json.loads(final_events[0]["data"])
    assert "couldn't reach an answer" in data["message"]["content"]
