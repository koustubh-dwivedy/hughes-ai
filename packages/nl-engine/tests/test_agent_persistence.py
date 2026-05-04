"""Round-trip tests for the LangChain ↔ canonical-JSON adapter."""

from __future__ import annotations

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from nl_engine.agent.persistence import from_canonical, to_canonical


def test_human_round_trip() -> None:
    msg = HumanMessage(content="What's our delinquency rate?")
    canonical = to_canonical(msg)
    assert canonical == {"role": "user", "content": "What's our delinquency rate?"}
    assert from_canonical(canonical).content == msg.content


def test_system_round_trip() -> None:
    msg = SystemMessage(content="You are a CU analyst.")
    canonical = to_canonical(msg)
    assert canonical["role"] == "system"
    assert from_canonical(canonical).content == msg.content


def test_assistant_with_tool_calls_round_trip() -> None:
    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "mf_query", "args": {"metric": "total_loans"}, "id": "abc"}
        ],
    )
    canonical = to_canonical(msg)
    assert canonical["role"] == "assistant"
    assert canonical["tool_calls"][0]["name"] == "mf_query"
    restored = from_canonical(canonical)
    assert isinstance(restored, AIMessage)
    assert restored.tool_calls[0]["args"]["metric"] == "total_loans"


def test_tool_message_round_trip() -> None:
    msg = ToolMessage(
        content='{"rows": []}',
        tool_call_id="abc",
        name="mf_query",
    )
    canonical = to_canonical(msg)
    assert canonical["role"] == "tool"
    assert canonical["tool_results"][0]["tool_call_id"] == "abc"
    restored = from_canonical(canonical)
    assert isinstance(restored, ToolMessage)
    assert restored.tool_call_id == "abc"


def test_assistant_content_list_coerced_to_string() -> None:
    msg = AIMessage(content=[{"type": "text", "text": "Hello"}])
    canonical = to_canonical(msg)
    assert canonical["content"] == "Hello"
