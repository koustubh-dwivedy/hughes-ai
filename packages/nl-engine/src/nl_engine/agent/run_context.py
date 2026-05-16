"""Agent run context: per-invocation event emitter callback (HUG-242).

Tools live in `nl_engine.agent` but the SSE channel and the typed event
factories live in `api.services.research_agent` — and the import-graph
rule forbids `nl_engine → api`. To bridge, the agent runner binds an
emitter callback via `bind_event_emitter(...)` before invoking the
compiled graph; tool bodies call `emit_run_event(name, payload)` and
the callback (registered in api-layer code) pushes the SSE event +
records telemetry.

If no callback is bound (tests, offline runs), `emit_run_event` is a
no-op — the DB writes are still the source of truth so the test can
inspect persistence directly.
"""

from __future__ import annotations

import contextvars
from collections.abc import Callable
from typing import Any

EventEmitter = Callable[[str, dict[str, Any]], None]

_emitter_var: contextvars.ContextVar[EventEmitter | None] = contextvars.ContextVar(
    "agent_run_event_emitter", default=None
)


def bind_event_emitter(
    emit: EventEmitter,
) -> contextvars.Token[EventEmitter | None]:
    """Bind an emitter for the calling async task. Returns the reset
    token; caller hands it to `reset_event_emitter` after the work."""
    return _emitter_var.set(emit)


def reset_event_emitter(token: contextvars.Token[EventEmitter | None]) -> None:
    _emitter_var.reset(token)


def emit_run_event(name: str, payload: dict[str, Any]) -> None:
    """Emit one event through the bound callback, or silently no-op
    when no callback is bound. The callback's contract is
    `(event_name, payload_dict) -> None`."""
    cb = _emitter_var.get()
    if cb is not None:
        cb(name, payload)
