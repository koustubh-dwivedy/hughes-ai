"""Chat-path persistence callback for `run_agent_isolated` (HUG-206).

Split out of `agent_runner.py` to keep that module under the 300-line
structural cap; the worker-path equivalent will land alongside in
S1 (`research_agent/worker_process_message.py`).

The chat callback persists every AI/Tool message to `thread_messages`
and emits the SSE events the chat surface consumes. Workers (S1)
replace this with a callback that persists to `research_findings`
instead — same shape, different sink.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, ToolMessage
from nl_engine.logging import get_logger

from api.services.agent_runner_events import (
    emit_step,
    emit_thinking,
    terminal_payload,
    trace_entry,
)
from api.services.agent_runner_persistence import persist_assistant, persist_tool
from api.services.openui_validator import validate_openui_dsl
from api.types.threads_api import StreamFinal

_slog = get_logger().bind(component="agent.runner")


def _final_event(persisted: Any, openui: Any) -> dict[str, Any]:
    """Build the `event: final` SSE payload for one persisted message."""
    return {
        "event": "final",
        "data": StreamFinal(message=persisted, openui=openui).model_dump_json(),
    }


def chat_process_message(
    msg: Any,
    step_idx: int,
    thread_id: UUID,
    db_url: str,
    trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per-message side effects for the chat path: persist the message
    to `thread_messages` and emit thinking / step / final SSE events.

    Workers will provide a sibling callback that persists to
    `research_findings` instead.

    `trace` accumulates the chronological agent narration for the turn
    and is persisted onto the final-answer ToolMessage so the
    References modal can show the full audit trail post-completion.
    """
    out: list[dict[str, Any]] = []
    thinking = emit_thinking(msg, step_idx)
    if thinking is not None:
        _slog.info(
            "agent.narration_emitted",
            message_idx=step_idx,
            msg_kind=type(msg).__name__,
        )
        out.append(thinking)
        trace.append(trace_entry(msg, step_idx, _line_from(thinking)))
    step_event = emit_step(msg, step_idx)
    if step_event is not None:
        out.append(step_event)
    if isinstance(msg, AIMessage):
        # HUG-265: when the turn ends with prose + no tool_calls (graph
        # routes to END without ever producing a final_answer
        # ToolMessage), synthesize an event:final so the SSE consumer
        # closes cleanly. Also covers _step_cap_node's plaintext exit.
        persisted_ai = persist_assistant(thread_id, msg, db_url)
        if not msg.tool_calls:
            out.append(_final_event(persisted_ai, openui=None))
    elif isinstance(msg, ToolMessage):
        terminal = terminal_payload(msg)
        persisted = persist_tool(
            thread_id,
            msg,
            db_url,
            terminal=terminal,
            thinking_trace=trace if terminal is not None else None,
        )
        if terminal is not None:
            dsl = terminal.get("openui_dsl")
            openui = (
                validate_openui_dsl(dsl)
                if isinstance(dsl, str) and dsl
                else None
            )
            _slog.info("agent.trace_persisted", entries=len(trace))
            out.append(_final_event(persisted, openui=openui))
    return out


def _line_from(thinking_event: dict[str, Any]) -> str:
    """Extract the line from a serialized SSE thinking event."""
    try:
        return str(
            json.loads(thinking_event.get("data", "{}")).get("line", "")
        )
    except (ValueError, AttributeError):
        return ""
