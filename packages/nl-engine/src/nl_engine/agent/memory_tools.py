"""Lead-agent external memory tools (HUG-241 + Fix C, 2026-05-17).

`read_memory(key)` and `write_memory(key, body)` back the lead's keyed
scratchpad in `research_lead_notes`. They resolve the current `plan_id`
DYNAMICALLY from `thread_id` via `get_latest_plan_id` at tool-call time,
because the placeholder uuid4 the runner bound at thread start doesn't
satisfy the FK on `research_lead_notes.plan_id` (Fix C — E2E
verification found this regression on 2026-05-17).

Behaviour when no plan exists yet (the lead called write_memory BEFORE
its first propose_plan):
  - `read_memory` returns `{"body": null}` — no error, just empty.
  - `write_memory` returns `{"error": "no_plan_for_thread"}` so the
    lead can recover by calling propose_plan first.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from nl_engine.agent.memory_context import (
    MemoryContextNotBoundError,
    current_db_url,
    current_thread_id,
)
from nl_engine.logging import get_logger
from nl_engine.repo.lead_memory import (
    MAX_NOTE_CHARS,
    read_lead_note_by_key,
    write_lead_note,
)
from nl_engine.repo.plans import get_latest_plan_id

slog = get_logger().bind(component="agent.memory_tools")


def _resolve_context() -> tuple[Any, str] | dict[str, Any]:
    """Return `(plan_id, db_url)` if a plan exists for the current
    thread, else an error dict the caller can return verbatim."""
    try:
        thread_id = current_thread_id()
        db_url = current_db_url()
    except MemoryContextNotBoundError as exc:
        slog.warning("agent.memory.unbound", error=str(exc))
        return {"error": "memory_context_not_bound"}
    plan_id = get_latest_plan_id(thread_id, db_url)
    if plan_id is None:
        return {"error": "no_plan_for_thread"}
    return plan_id, db_url


@tool
def read_memory(key: str) -> dict[str, Any]:
    """Read the latest note you previously wrote under `key`.

    Use to recall a finding, a partial summary, or a plan-step note
    you saved between subagent dispatches. Returns
    `{"body": "<your note>"}` or `{"body": null}` if no note exists
    for that key. Notes are scoped to the current plan; calling before
    you've issued `propose_plan` also returns `{"body": null}`.

    Pair with `write_memory(key, body)`. Pick stable keys per
    semantic slot (e.g., `"after_step_1"`, `"branches_with_delta"`)
    so successive writes append a new version under the same slot.
    """
    resolved = _resolve_context()
    if isinstance(resolved, dict):
        # No plan yet → return null body (read is forgiving), but
        # surface the underlying cause in case the caller cares.
        if resolved.get("error") == "no_plan_for_thread":
            return {"body": None}
        return {"body": None, **resolved}
    plan_id, db_url = resolved
    body = read_lead_note_by_key(plan_id, key, db_url)
    slog.info("agent.read_memory", key=key, hit=body is not None)
    return {"body": body}


@tool
def write_memory(key: str, body: str) -> dict[str, Any]:
    """Persist a note under `key` for later recall via `read_memory`.

    Notes are bound to the CURRENT research plan — call `propose_plan`
    at least once before writing. Successive writes under the same key
    append new versions; `read_memory` returns the latest.

    Bodies > ~2000 chars are truncated. The result indicates
    `{"version": N, "truncated": bool, "stored_chars": N}`.
    Prefer concise factual notes over verbose narrative.
    """
    resolved = _resolve_context()
    if isinstance(resolved, dict):
        return resolved  # error dict
    plan_id, db_url = resolved
    result = write_lead_note(plan_id, key, body, db_url)
    slog.info(
        "agent.write_memory",
        key=key,
        version=result.version,
        truncated=result.truncated,
        stored_chars=len(result.body),
        cap=MAX_NOTE_CHARS,
    )
    return {
        "version": result.version,
        "truncated": result.truncated,
        "stored_chars": len(result.body),
    }


LEAD_AGENT_MEMORY_TOOLS = [
    read_memory,
    write_memory,
]
