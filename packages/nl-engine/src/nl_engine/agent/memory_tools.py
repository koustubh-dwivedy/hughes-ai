"""Lead-agent external memory tools (HUG-241).

`read_memory(key)` and `write_memory(key, body)` back the lead's keyed
scratchpad in `research_lead_notes`. Both resolve `plan_id` + `db_url`
via the contextvars in `memory_context` so the tool signature visible
to the LLM stays semantically clean — just `key` (and `body` on write).

The agent runner (HUG-244) binds the context before invoking the
compiled graph; tests bind it directly around the tool invocation.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from nl_engine.agent.memory_context import (
    MemoryContextNotBoundError,
    current_db_url,
    current_plan_id,
)
from nl_engine.logging import get_logger
from nl_engine.repo.lead_memory import (
    MAX_NOTE_CHARS,
    read_lead_note_by_key,
    write_lead_note,
)

slog = get_logger().bind(component="agent.memory_tools")


@tool
def read_memory(key: str) -> dict[str, Any]:
    """Read the latest note you previously wrote under `key`.

    Use to recall a finding, a partial summary, or a plan-step note
    you saved between subagent dispatches. Returns
    `{"body": "<your note>"}` or `{"body": null}` if no note exists
    for that key. Keys are plan-scoped; a new plan starts with a
    fresh memory.

    Pair with `write_memory(key, body)`. Pick stable keys per
    semantic slot (e.g., `"after_step_1"`, `"branches_with_delta"`)
    rather than free-form strings so successive writes append a new
    version under the same slot.
    """
    try:
        plan_id = current_plan_id()
        db_url = current_db_url()
    except MemoryContextNotBoundError as exc:
        slog.warning("agent.read_memory.unbound", error=str(exc))
        return {"body": None, "error": "memory_context_not_bound"}
    body = read_lead_note_by_key(plan_id, key, db_url)
    slog.info("agent.read_memory", key=key, hit=body is not None)
    return {"body": body}


@tool
def write_memory(key: str, body: str) -> dict[str, Any]:
    """Persist a note under `key` for later recall via `read_memory`.

    Use BETWEEN subagent dispatches to summarise findings, capture
    interim plan revisions, or record what's left to do. Notes are
    plan-scoped (a new plan starts fresh) and versioned per
    `(plan_id, key)` — successive writes preserve history without
    overwriting; `read_memory` returns the latest.

    Bodies longer than ~2000 chars are truncated. The model output
    indicates `{"version": N, "truncated": bool, "stored_chars": N}`.
    Prefer concise, factual notes over verbose narrative.
    """
    try:
        plan_id = current_plan_id()
        db_url = current_db_url()
    except MemoryContextNotBoundError as exc:
        slog.warning("agent.write_memory.unbound", error=str(exc))
        return {"error": "memory_context_not_bound"}
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
