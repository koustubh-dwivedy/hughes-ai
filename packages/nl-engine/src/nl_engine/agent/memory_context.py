"""Context binding for the lead agent's `read_memory` / `write_memory`
tools (HUG-241).

LangChain `@tool` functions receive only their declared argument list —
they have no access to the agent state. The memory tools need two
pieces of execution context that vary per turn: the current `plan_id`
(which is the partition key for the keyed scratchpad in
`research_lead_notes`) and the DB URL. We pass them through Python
contextvars rather than the tool argument list because:

1. The LLM should NOT see plan_id or db_url in the tool signature —
   those would be additional fields it might hallucinate, increase
   prompt token count, and aren't conceptually part of "memory."
2. Contextvars are async-task-safe; LangGraph's async invocation
   model preserves the context across tool calls.

The agent runner (HUG-244) calls `bind_memory_context(plan_id, db_url)`
before invoking `compiled_graph.ainvoke(...)` and resets on exit. Tests
bind the context manually around the tool invocation.
"""

from __future__ import annotations

import contextvars
from uuid import UUID

_plan_id_var: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "lead_agent_plan_id", default=None
)
_db_url_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "lead_agent_db_url", default=None
)
_thread_id_var: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "lead_agent_thread_id", default=None
)


class MemoryContextNotBoundError(RuntimeError):
    """Raised when a memory tool is called without context bound. Surfaces
    a clear configuration error rather than a silent NoneType crash."""


def bind_memory_context(
    plan_id: UUID,
    db_url: str,
    thread_id: UUID | None = None,
) -> tuple[
    contextvars.Token[UUID | None],
    contextvars.Token[str | None],
    contextvars.Token[UUID | None],
]:
    """Bind plan_id, db_url, and optionally thread_id for the calling
    async task. Returns the reset tokens; the caller must hand them to
    `reset_memory_context`."""
    return (
        _plan_id_var.set(plan_id),
        _db_url_var.set(db_url),
        _thread_id_var.set(thread_id),
    )


def reset_memory_context(
    tokens: tuple[
        contextvars.Token[UUID | None],
        contextvars.Token[str | None],
        contextvars.Token[UUID | None],
    ],
) -> None:
    _plan_id_var.reset(tokens[0])
    _db_url_var.reset(tokens[1])
    _thread_id_var.reset(tokens[2])


def current_plan_id() -> UUID:
    pid = _plan_id_var.get()
    if pid is None:
        raise MemoryContextNotBoundError(
            "read_memory / write_memory called without plan_id bound. "
            "The agent runner must call bind_memory_context before "
            "dispatching tools."
        )
    return pid


def current_db_url() -> str:
    durl = _db_url_var.get()
    if durl is None:
        raise MemoryContextNotBoundError(
            "read_memory / write_memory called without db_url bound. "
            "The agent runner must call bind_memory_context before "
            "dispatching tools."
        )
    return durl


def current_thread_id() -> UUID:
    tid = _thread_id_var.get()
    if tid is None:
        raise MemoryContextNotBoundError(
            "propose_plan called without thread_id bound. The agent "
            "runner must include thread_id in bind_memory_context."
        )
    return tid
