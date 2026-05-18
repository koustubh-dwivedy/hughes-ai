"""ContextVar carrying the active `turn_id` (HUG-266).

`start_lead_turn` binds the turn_id before iterating the agent
generator; `persist_assistant` / `persist_tool` read it and tag every
inserted `thread_messages` row with that turn_id. The tail SSE
producer then filters by `turn_id` so a reload reconnects to exactly
the turn that was in flight.

Mirrors `nl_engine.agent.memory_context` — same context-var pattern,
same async-task-safety guarantees. Returning None when unbound is
deliberate: persist_* paths called outside a turn (e.g. tests writing
sample rows directly) still work, they just write NULL for turn_id.
"""

from __future__ import annotations

import contextvars
from uuid import UUID

_turn_id_var: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "active_turn_id", default=None
)


def bind_turn_context(turn_id: UUID) -> contextvars.Token[UUID | None]:
    """Bind `turn_id` for the duration of the current task. Caller MUST
    pass the returned token to `reset_turn_context` when done."""
    return _turn_id_var.set(turn_id)


def reset_turn_context(token: contextvars.Token[UUID | None]) -> None:
    _turn_id_var.reset(token)


def current_turn_id() -> UUID | None:
    """The active turn_id, or None when persist_* is called outside a
    fire-and-forget agent turn (e.g. tests, ad-hoc writes)."""
    return _turn_id_var.get()
