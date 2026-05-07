"""SSE event construction + trace-entry helpers for the agent runner.

Lives outside `agent_runner.py` to keep that module under the 300-line
structural cap; pure functions that turn agent messages into the
`{event, data}` dicts the route layer hands to sse_starlette and into
the persistent trace entries shown in the References modal.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from api.services.agent_narration import narration_for
from api.types.threads_api import StreamStep, StreamThinking


def emit_step(msg: Any, step_idx: int) -> dict[str, Any] | None:
    def _step(**kw: Any) -> dict[str, Any]:
        data = StreamStep(step=step_idx, **kw).model_dump_json()
        return {"event": "step", "data": data}

    if isinstance(msg, AIMessage) and msg.tool_calls:
        first = msg.tool_calls[0]
        return _step(kind="tool_call", name=first["name"], args=first.get("args"))
    if isinstance(msg, ToolMessage):
        try:
            result = json.loads(str(msg.content))
        except (json.JSONDecodeError, TypeError):
            result = None
        return _step(
            kind="tool_result",
            name=msg.name,
            result=result if isinstance(result, dict) else None,
        )
    if isinstance(msg, AIMessage):
        return _step(kind="thinking", result=None)
    return None


def emit_thinking(msg: Any, step_idx: int) -> dict[str, Any] | None:
    """Synthesize the rolling-line narration event for the Thinking
    box (HUG-202 Phase 1)."""
    line = narration_for(msg)
    if line is None:
        return None
    return {
        "event": "thinking",
        "data": StreamThinking(step=step_idx, line=line).model_dump_json(),
    }


def trace_kind(msg: Any) -> str:
    if isinstance(msg, AIMessage):
        return "tool_call" if msg.tool_calls else "thinking_text"
    if isinstance(msg, ToolMessage):
        return "tool_result"
    return "other"


def tool_name(msg: Any) -> str | None:
    if isinstance(msg, AIMessage) and msg.tool_calls:
        first = msg.tool_calls[0]
        name = first.get("name")
        return name if isinstance(name, str) else None
    if isinstance(msg, ToolMessage):
        return msg.name
    return None


def trace_entry(msg: Any, step_idx: int, line: str) -> dict[str, Any]:
    """Build a chronological audit entry for the References modal."""
    return {
        "step": step_idx,
        "kind": trace_kind(msg),
        "label": line,
        "tool": tool_name(msg),
        "at": datetime.now(UTC).isoformat(),
    }


def terminal_payload(msg: ToolMessage) -> dict[str, Any] | None:
    """Decoded `final_answer` JSON payload, or None when this isn't a
    final-answer ToolMessage."""
    if msg.name != "final_answer":
        return None
    try:
        decoded = json.loads(str(msg.content))
    except (json.JSONDecodeError, TypeError):
        return None
    return decoded if isinstance(decoded, dict) else None
