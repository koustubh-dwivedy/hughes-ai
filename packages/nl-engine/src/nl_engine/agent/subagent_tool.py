"""Lead-agent `run_subagent` tool — batch dispatch (Issue 1, 2026-05-17).

The lead emits ONE `run_subagent` call with a LIST of sub-questions.
Each entry spawns a worker that runs its own ReAct loop with
`max_steps=10` and a restricted tool registry (data tools only — no
recursive subagent dispatch, no plan, no memory). Workers fan out in
parallel via a thread pool so wall-clock is max(worker_durations), not
sum, and the lead spends ONE step on dispatching the whole batch.

The previous one-sub-question-per-call shape forced the LLM to
serialise delegation across LLM turns — a typical deep question burned
8-12 lead LLM calls just for fan-out, often exhausting the 20-step
budget before final_answer. Batching collapses that to a single call.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
from nl_engine.repo.plans import get_latest_plan_id

slog = get_logger().bind(component="agent.subagent_tool")

WORKER_MAX_STEPS = 10
# Cap per batch — high enough for realistic decompositions (YoY by 6
# branches, 4 metrics x 3 windows, etc.) but low enough that a runaway
# lead can't spawn 50 workers at once.
MAX_SUBAGENTS_PER_BATCH = 8
# Parallelism cap inside one batch. Workers are LLM-bound + occasional
# subprocess (mf CLI); 4 concurrent is a safe ceiling for the Groq tier
# we run on without rate-limiting the queue.
WORKER_POOL_MAX_WORKERS = 4


def _build_worker_graph() -> Any:
    """Compile a fresh ReAct graph for the worker with data tools only."""
    # Local imports — tools.py → plan_tool → subagent_tool would cycle.
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


def _record_failure(call_id: Any, db_url: str, err: str) -> dict[str, Any]:
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


def _spawn_pending(
    sub: dict[str, Any],
    thread_id: Any,
    plan_id: Any,
    db_url: str,
) -> tuple[Any, str, int | None]:
    """Insert + mark_running + emit spawned event. Returns (call_id, prompt,
    plan_step_ordinal) for the worker pool."""
    prompt = str(sub.get("prompt") or sub.get("question") or "")
    raw_ordinal = sub.get("plan_step_ordinal")
    ordinal = int(raw_ordinal) if isinstance(raw_ordinal, int) else None
    call_id = subagent_calls.insert_pending(
        thread_id=thread_id,
        plan_id=plan_id,
        prompt=prompt,
        plan_step_ordinal=ordinal,
        db_url=db_url,
    )
    emit_run_event(
        "research.subagent.spawned",
        {
            "call_id": str(call_id),
            "thread_id": str(thread_id),
            "prompt": prompt,
            "plan_step_ordinal": ordinal,
        },
    )
    subagent_calls.mark_running(call_id, db_url)
    return call_id, prompt, ordinal


def _run_one(entry: tuple[Any, str, int | None]) -> dict[str, Any]:
    """Worker-thread body: invoke the worker graph, return raw outcome.
    Emission + DB completion happens on the caller thread so contextvars
    (event emitter) don't need to be propagated across threads."""
    call_id, prompt, _ordinal = entry
    try:
        final = _invoke_worker(prompt, request_id=str(call_id))
        return {"call_id": call_id, "final": final, "exc": None}
    except Exception as worker_exc:  # noqa: BLE001 — boundary
        return {"call_id": call_id, "final": None, "exc": worker_exc}


def _finalize_batch(
    raw_results: list[dict[str, Any]],
    thread_id: Any,
    db_url: str,
) -> list[dict[str, Any]]:
    """Phase 3: persist completion + emit events for each worker outcome.
    Runs on the caller thread where contextvars (event emitter) are bound."""
    out: list[dict[str, Any]] = []
    for raw in raw_results:
        call_id = raw["call_id"]
        raw_exc = raw["exc"]
        if raw_exc is not None:
            slog.warning(
                "agent.run_subagent.worker_exception",
                call_id=str(call_id),
                error_type=type(raw_exc).__name__,
            )
            out.append(
                _record_failure(
                    call_id, db_url, f"{type(raw_exc).__name__}: {raw_exc}"
                )
            )
        elif raw["final"] is None:
            slog.warning(
                "agent.run_subagent.no_final_answer", call_id=str(call_id)
            )
            out.append(
                _record_failure(
                    call_id, db_url, "worker did not produce final_answer"
                )
            )
        else:
            out.append(
                _record_success(call_id, thread_id, raw["final"], db_url)
            )
    return out


@tool
def run_subagent(subagents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dispatch MULTIPLE worker subagents in PARALLEL — one call covers
    the whole fan-out for the current research step.

    Args:
        subagents: list of `{"prompt": str, "plan_step_ordinal": int?}`.
            Each entry spawns one worker. Max 8 per batch. Each worker
            runs its own ReAct loop (10 steps max) with only the data
            tools (list_metrics, lookup_metric_definition, mf_query,
            clarify, final_answer). Workers cannot recurse.

    Returns:
        list of `{"summary", "rows", "mf_query", "call_id"}` (or
        `{"error", "call_id"}` on failure), one entry per input,
        preserving input order.

    Always dispatch the COMPLETE batch of sub-questions for the current
    step in ONE call. Don't call run_subagent serially across turns —
    you only get 20 LLM calls per turn.
    """
    if not isinstance(subagents, list):
        return [{"error": "subagents must be a list"}]
    if len(subagents) == 0:
        return []
    if len(subagents) > MAX_SUBAGENTS_PER_BATCH:
        return [
            {
                "error": (
                    f"too many subagents in one batch: {len(subagents)} > "
                    f"{MAX_SUBAGENTS_PER_BATCH}. Split into smaller batches."
                )
            }
        ]
    try:
        thread_id = current_thread_id()
        db_url = current_db_url()
    except MemoryContextNotBoundError as exc:
        slog.warning("agent.run_subagent.unbound", error=str(exc))
        return [{"error": "agent_context_not_bound"}]

    # Bind subagent_calls rows to the lead's active plan (if any) so the
    # audit panel (`/plans/{pid}/subagent-calls`) returns them. Without
    # this each row is plan_id=NULL and the panel renders empty rows.
    plan_id = get_latest_plan_id(thread_id, db_url)

    # Phase 1: persist + emit spawned (sequential — fast DB inserts).
    entries: list[tuple[Any, str, int | None]] = [
        _spawn_pending(sub, thread_id, plan_id, db_url) for sub in subagents
    ]
    slog.info(
        "agent.run_subagent.batch_dispatched",
        batch_size=len(entries),
        max_workers=WORKER_POOL_MAX_WORKERS,
    )

    # Phase 2: fan out worker invocations on a thread pool.
    pool_size = min(len(entries), WORKER_POOL_MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=pool_size) as pool:
        raw_results = list(pool.map(_run_one, entries))

    # Phase 3: persist + emit events (caller thread, contextvars bound).
    return _finalize_batch(raw_results, thread_id, db_url)
