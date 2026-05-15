"""Worker-path `process_message` callback (HUG-217, S1).

Mirrors `agent_runner_chat.chat_process_message` shape — same
`(msg, step_idx, thread_id, db_url, trace)` signature so it plugs
directly into `run_agent_isolated`. Two differences from the chat
callback:

  1. Persists to `research_findings` (when a `final_answer`
     ToolMessage arrives) instead of `thread_messages`.
  2. Emits `research.subagent.*` events to structlog instead of
     yielding SSE events for the chat surface. Worker progress is
     NOT surfaced on the user-facing chat stream; the coordinator
     re-emits aggregated step events from outside the worker.

Today the worker only persists on the FINAL message. Earlier
messages (interim AI/Tool exchanges within the worker's ReAct loop)
are observed via structlog only — they don't represent a "finding"
until the final_answer tool fires.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_core.messages import ToolMessage
from nl_engine.logging import get_logger

from api.repo import research_steps as steps_repo
from api.services.research_agent.telemetry import (
    EVENT_FINDING_PERSISTED,
    log_event,
)

_slog = get_logger().bind(component="research.worker")


def _parse_final_payload(msg: ToolMessage) -> dict[str, Any] | None:
    """ToolMessage from final_answer is a JSON string. Parse it; on
    any failure, return None and rely on the caller to skip
    persistence (worker still finishes, but no row written)."""
    if msg.name != "final_answer":
        return None
    content = msg.content
    if not isinstance(content, str):
        return None
    try:
        out = json.loads(content)
    except (ValueError, TypeError):
        return None
    return out if isinstance(out, dict) else None


def make_worker_process_message(
    *, step_id: UUID,
) -> Callable[[Any, int, UUID, str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Factory that closes over the `step_id` so the callback
    matches `ProcessMessageFn`'s 5-arg signature without
    smuggling extra params through `run_agent_isolated`."""

    def _persist(
        msg: Any,
        step_idx: int,
        thread_id: UUID,   # unused for worker path — kept for signature parity
        db_url: str,
        trace: list[dict[str, Any]],   # unused for worker path
    ) -> list[dict[str, Any]]:
        del thread_id, trace  # quiet unused-arg lint
        if not isinstance(msg, ToolMessage):
            return []
        payload = _parse_final_payload(msg)
        if payload is None:
            return []
        # final_answer payload: {summary, rows?, mf_query?, openui_dsl?, …}
        finding = steps_repo.append_finding(
            step_id=step_id,
            db_url=db_url,
            summary_text=payload.get("summary"),
            structured_rows_json=payload.get("rows"),
            mf_query_json=payload.get("mf_query"),
            cited_artifacts=payload.get("citations"),
        )
        log_event(
            EVENT_FINDING_PERSISTED,
            step_id=str(step_id),
            finding_id=str(finding.finding_id),
            step_idx=step_idx,
            has_rows=bool(payload.get("rows")),
            has_mf_query=payload.get("mf_query") is not None,
        )
        _slog.info(
            "worker.finding_persisted",
            step_id=str(step_id),
            finding_id=str(finding.finding_id),
        )
        return []   # workers don't emit SSE events to the chat stream

    return _persist
