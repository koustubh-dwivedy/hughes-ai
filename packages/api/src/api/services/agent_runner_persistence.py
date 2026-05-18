"""Persistence-side helpers for agent_runner.py — extracted to keep
the runner under the 300-line structural cap (HUG-202 Phase 3)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, ToolMessage
from nl_engine.agent.persistence import to_canonical

from api.repo import threads as threads_repo
from api.services.turn_context import current_turn_id
from api.types.threads import ThreadMessage


def persist_assistant(
    thread_id: UUID, msg: AIMessage, db_url: str
) -> ThreadMessage:
    canonical = to_canonical(msg)
    return threads_repo.append_message(
        thread_id=thread_id,
        role="assistant",
        db_url=db_url,
        content=canonical.get("content") or "",
        tool_calls=canonical.get("tool_calls"),
        turn_id=current_turn_id(),
    )


def persist_tool(
    thread_id: UUID,
    msg: ToolMessage,
    db_url: str,
    terminal: dict[str, Any] | None = None,
    thinking_trace: list[dict[str, Any]] | None = None,
) -> ThreadMessage:
    """Persist a tool message. When `terminal` is the decoded
    `final_answer` payload, also propagate openui_dsl / mf_query /
    rows / thinking_trace into their dedicated columns so reloading a
    thread via GET /threads/:id renders with full fidelity."""
    canonical = to_canonical(msg)
    extra: dict[str, Any] = {}
    if terminal is not None:
        dsl = terminal.get("openui_dsl")
        if isinstance(dsl, str) and dsl:
            extra["openui_dsl"] = dsl
        mf = terminal.get("mf_query")
        if isinstance(mf, dict):
            extra["mf_query"] = mf
        rows = terminal.get("rows")
        if isinstance(rows, list):
            extra["rows"] = rows
    if thinking_trace is not None:
        extra["thinking_trace"] = thinking_trace
    return threads_repo.append_message(
        thread_id=thread_id,
        role="tool",
        db_url=db_url,
        content=canonical.get("content") or "",
        tool_results=canonical.get("tool_results"),
        turn_id=current_turn_id(),
        **extra,
    )
