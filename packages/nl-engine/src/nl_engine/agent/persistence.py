"""Adapter between LangChain `BaseMessage` and our canonical
`{role, content, tool_calls, tool_results}` JSON shape.

The canonical shape is what `thread_messages` stores, what the
frontend receives over the SSE stream, and what the eval harness
asserts against. Keeping the LangChain leak fully contained inside
the graph lets us swap LangGraph for something else without rewriting
the storage layer or the API surface.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

CanonicalMessage = dict[str, Any]


def to_canonical(msg: BaseMessage) -> CanonicalMessage:
    """LangChain BaseMessage → `{role, content, tool_calls?, tool_results?}`."""
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": _coerce_str(msg.content)}
    if isinstance(msg, SystemMessage):
        return {"role": "system", "content": _coerce_str(msg.content)}
    if isinstance(msg, AIMessage):
        out: CanonicalMessage = {
            "role": "assistant",
            "content": _coerce_str(msg.content),
        }
        if msg.tool_calls:
            out["tool_calls"] = [
                {"name": tc["name"], "args": tc.get("args", {}), "id": tc.get("id")}
                for tc in msg.tool_calls
            ]
        return out
    if isinstance(msg, ToolMessage):
        return {
            "role": "tool",
            "content": _coerce_str(msg.content),
            "tool_results": [
                {
                    "tool_call_id": msg.tool_call_id,
                    "name": getattr(msg, "name", None),
                    "result": _coerce_str(msg.content),
                }
            ],
        }
    raise ValueError(f"Unsupported BaseMessage subclass: {type(msg).__name__}")


def from_canonical(msg: CanonicalMessage) -> BaseMessage:
    """Inverse of to_canonical(). Round-trips for every supported role."""
    role = msg.get("role")
    content = msg.get("content", "") or ""
    if role == "user":
        return HumanMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    if role == "assistant":
        tool_calls = [
            {"name": tc["name"], "args": tc.get("args", {}), "id": tc.get("id")}
            for tc in msg.get("tool_calls") or []
        ]
        return AIMessage(content=content, tool_calls=tool_calls)
    if role == "tool":
        results = msg.get("tool_results") or [{}]
        first = results[0]
        return ToolMessage(
            content=str(first.get("result", content)),
            tool_call_id=first.get("tool_call_id", "unknown"),
            name=first.get("name"),
        )
    raise ValueError(f"Unsupported canonical role: {role!r}")


def _coerce_str(content: Any) -> str:
    """LangChain's BaseMessage.content can be str | list; coerce to str."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)
