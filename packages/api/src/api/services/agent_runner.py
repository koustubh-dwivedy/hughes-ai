"""Runs a user turn through the LangGraph agent and persists every
canonical message as it streams back. Emits SSE-friendly events so the
route layer just has to forward them.

The runner is async-friendly (FastAPI route is async) but the underlying
graph is sync; we run the synchronous stream in a thread executor so
the event loop isn't blocked by Cerebras latency.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from nl_engine.agent.graph import build_graph
from nl_engine.agent.persistence import to_canonical
from nl_engine.agent.state import AgentState

from api.repo import threads as threads_repo
from api.services.openui_validator import validate_openui_dsl
from api.types.threads import ThreadMessage
from api.types.threads_api import StreamFinal, StreamStep

log = logging.getLogger(__name__)


def _persist_assistant(
    thread_id: UUID, msg: AIMessage, db_url: str
) -> ThreadMessage:
    canonical = to_canonical(msg)
    return threads_repo.append_message(
        thread_id=thread_id,
        role="assistant",
        db_url=db_url,
        content=canonical.get("content") or "",
        tool_calls=canonical.get("tool_calls"),
    )


def _persist_tool(
    thread_id: UUID, msg: ToolMessage, db_url: str
) -> ThreadMessage:
    canonical = to_canonical(msg)
    return threads_repo.append_message(
        thread_id=thread_id,
        role="tool",
        db_url=db_url,
        content=canonical.get("content") or "",
        tool_results=canonical.get("tool_results"),
    )


def _terminal_payload(msg: ToolMessage) -> dict[str, Any] | None:
    """If this ToolMessage is a `final_answer` result, decode its JSON
    payload so the SSE final event carries structured data."""
    if msg.name != "final_answer":
        return None
    try:
        decoded = json.loads(str(msg.content))
    except (json.JSONDecodeError, TypeError):
        return None
    return decoded if isinstance(decoded, dict) else None


async def stream_user_turn(
    thread_id: UUID,
    user_content: str,
    db_url: str,
    llm: BaseChatModel,
    history: list[ThreadMessage],
) -> AsyncIterator[dict[str, Any]]:
    """Persist the user message, run the agent, yield SSE events.

    Each event is a dict ready for sse_starlette.EventSourceResponse:
      {event: "step", data: <json>} or {event: "final", data: <json>}.
    """
    threads_repo.append_message(
        thread_id=thread_id,
        role="user",
        db_url=db_url,
        content=user_content,
    )
    initial = _build_initial_state(thread_id, user_content, history)
    graph = build_graph(llm)
    queue: asyncio.Queue[Any] = asyncio.Queue()

    def producer() -> None:
        try:
            for chunk in graph.stream(initial, stream_mode="values"):
                queue.put_nowait(chunk)
        finally:
            queue.put_nowait(None)

    asyncio.create_task(asyncio.to_thread(producer))
    seen: set[int] = set()
    step_idx = 0
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        for msg in chunk.get("messages", []):
            if id(msg) in seen or isinstance(msg, HumanMessage):
                seen.add(id(msg))
                continue
            seen.add(id(msg))
            step_idx += 1
            for event in _process_message(msg, step_idx, thread_id, db_url):
                yield event


def _process_message(
    msg: Any, step_idx: int, thread_id: UUID, db_url: str
) -> list[dict[str, Any]]:
    """Per-message side effects: persist + emit step (+ maybe final)."""
    out: list[dict[str, Any]] = []
    event = _emit(msg, step_idx)
    if event is not None:
        out.append(event)
    if isinstance(msg, AIMessage):
        _persist_assistant(thread_id, msg, db_url)
    elif isinstance(msg, ToolMessage):
        persisted = _persist_tool(thread_id, msg, db_url)
        terminal = _terminal_payload(msg)
        if terminal is not None:
            dsl = terminal.get("openui_dsl")
            openui = (
                validate_openui_dsl(dsl) if isinstance(dsl, str) and dsl else None
            )
            out.append(
                {
                    "event": "final",
                    "data": StreamFinal(
                        message=persisted, openui=openui
                    ).model_dump_json(),
                }
            )
    return out


def _build_initial_state(
    thread_id: UUID,
    user_content: str,
    history: list[ThreadMessage],
) -> AgentState:
    """Assemble the message list passed to the graph: prior messages
    (recovered from thread_messages) + the new user message."""
    from nl_engine.agent.persistence import from_canonical

    prior = [
        from_canonical(
            {
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_results": m.tool_results,
            }
        )
        for m in history
        if m.role in {"user", "assistant", "tool", "system"}
    ]
    prior.append(HumanMessage(content=user_content))
    return AgentState(messages=prior, thread_id=str(thread_id))


def _emit(msg: Any, step_idx: int) -> dict[str, Any] | None:
    if isinstance(msg, AIMessage) and msg.tool_calls:
        first = msg.tool_calls[0]
        return {
            "event": "step",
            "data": StreamStep(
                step=step_idx,
                kind="tool_call",
                name=first["name"],
                args=first.get("args"),
            ).model_dump_json(),
        }
    if isinstance(msg, ToolMessage):
        try:
            result = json.loads(str(msg.content))
        except (json.JSONDecodeError, TypeError):
            result = None
        return {
            "event": "step",
            "data": StreamStep(
                step=step_idx,
                kind="tool_result",
                name=msg.name,
                result=result if isinstance(result, dict) else None,
            ).model_dump_json(),
        }
    if isinstance(msg, AIMessage):
        return {
            "event": "step",
            "data": StreamStep(
                step=step_idx, kind="thinking", result=None
            ).model_dump_json(),
        }
    return None
