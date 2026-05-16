"""Lead-agent `run_subagent` tool (HUG-243).

Recursively dispatches a worker subagent for a focused sub-question.
The worker runs its own ReAct loop with `max_steps=10` and a RESTRICTED
tool registry — only the data tools (`list_metrics`,
`lookup_metric_definition`, `mf_query`, `clarify`, `final_answer`).
Workers cannot recurse: they don't see `run_subagent`, `propose_plan`,
or the memory tools.

Per-invocation graph compilation rather than runtime tool restriction
on a shared compiled graph — simpler, easier to test, and decouples us
from LangGraph internals.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

from nl_engine.agent.memory_context import (
    MemoryContextNotBoundError,
    current_db_url,
    current_thread_id,
)
from nl_engine.agent.run_context import emit_run_event
from nl_engine.agent.state import AgentState
from nl_engine.logging import get_logger
from nl_engine.repo import subagent_calls

slog = get_logger().bind(component="agent.subagent_tool")

WORKER_MAX_STEPS = 10


def _build_worker_graph() -> Any:
    """Compile a fresh ReAct graph for the worker with data tools only.

    Picks the LLM via `make_llm(role="worker")` so the user can route
    workers to a smaller/cheaper model when desired (config/llm.yaml
    `roles.worker` block); falls back to the top-level LLM otherwise.
    """
    # Imports here, not at module top, to avoid a circular import:
    # tools.py imports plan_tool which imports subagent_tool, but
    # subagent_tool wants the chat ALL_TOOLS list to build the worker.
    from nl_engine.agent.graph import build_graph
    from nl_engine.agent.tools import ALL_TOOLS
    from nl_engine.llm.factory import make_llm

    return build_graph(make_llm(role="worker"), tools=ALL_TOOLS)


def _extract_final_answer(messages: list[Any]) -> dict[str, Any] | None:
    """Walk messages backwards; return parsed final_answer ToolMessage
    payload (already-dict form), or None if no final_answer fired."""
    import json

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "final_answer":
            content = msg.content
            if isinstance(content, dict):
                return dict(content)
            if isinstance(content, str):
                try:
                    parsed: Any = json.loads(content)
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return {"summary": content}
            return None
    return None


def _invoke_worker(prompt: str, request_id: str) -> dict[str, Any] | None:
    state = AgentState(
        messages=[HumanMessage(content=prompt)],
        thread_id=f"worker-{uuid4()}",
        max_steps=WORKER_MAX_STEPS,
        request_id=request_id,
    )
    graph = _build_worker_graph()
    result = graph.invoke(state)
    messages = result.get("messages", []) if isinstance(result, dict) else []
    return _extract_final_answer(messages)


def _record_failure(
    call_id: Any, db_url: str, err: str
) -> dict[str, Any]:
    subagent_calls.mark_failed(call_id, err, db_url)
    emit_run_event(
        "research.subagent.failed",
        {"call_id": str(call_id), "error": err},
    )
    return {"error": err, "call_id": str(call_id)}


def _record_success(
    call_id: Any,
    thread_id: Any,
    final: dict[str, Any],
    db_url: str,
) -> dict[str, Any]:
    summary = final.get("summary")
    rows = final.get("rows")
    mf_query = final.get("mf_query")
    subagent_calls.mark_complete(call_id, summary, rows, mf_query, db_url)
    emit_run_event(
        "research.subagent.completed",
        {
            "call_id": str(call_id),
            "thread_id": str(thread_id),
            "summary_len": len(summary or ""),
            "row_count": len(rows or []),
        },
    )
    return {
        "summary": summary,
        "rows": rows,
        "mf_query": mf_query,
        "call_id": str(call_id),
    }


@tool
def run_subagent(prompt: str, plan_step_ordinal: int | None = None) -> dict[str, Any]:
    """Dispatch a worker subagent for one focused sub-question.

    The subagent runs its own ReAct loop with 10 steps max, using only
    the data tools (list_metrics, lookup_metric_definition, mf_query,
    clarify, final_answer). It cannot call propose_plan, run_subagent,
    or memory tools.

    Returns {summary, rows, mf_query} from its final_answer.
    Persists to subagent_calls table.
    """
    try:
        thread_id = current_thread_id()
        db_url = current_db_url()
    except MemoryContextNotBoundError as exc:
        slog.warning("agent.run_subagent.unbound", error=str(exc))
        return {"error": "agent_context_not_bound"}
    call_id = subagent_calls.insert_pending(
        thread_id=thread_id,
        plan_id=None,
        prompt=prompt,
        plan_step_ordinal=plan_step_ordinal,
        db_url=db_url,
    )
    emit_run_event(
        "research.subagent.spawned",
        {
            "call_id": str(call_id),
            "thread_id": str(thread_id),
            "prompt": prompt,
            "plan_step_ordinal": plan_step_ordinal,
        },
    )
    subagent_calls.mark_running(call_id, db_url)
    try:
        final = _invoke_worker(prompt, request_id=str(call_id))
    except Exception as exc:  # noqa: BLE001 — boundary
        slog.exception("agent.run_subagent.exception", call_id=str(call_id))
        return _record_failure(call_id, db_url, f"{type(exc).__name__}: {exc}")
    if final is None:
        slog.warning("agent.run_subagent.no_final_answer", call_id=str(call_id))
        return _record_failure(
            call_id, db_url, "worker did not produce final_answer within max_steps"
        )
    return _record_success(call_id, thread_id, final, db_url)
