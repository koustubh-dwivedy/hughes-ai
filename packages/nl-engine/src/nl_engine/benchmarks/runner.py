"""Per-question execution helpers + bridge between agent results and grader.

Surface 1 was retired in HUG-193, so the runner only handles the agent
path now. Long-tail agent grading is intentionally skipped (HUG-189
Option B) — see `agent_path_meaningful` for the rule.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from nl_engine.agent.eval_runner import AgentEvalResult, run_agent_question
from nl_engine.benchmarks.cache import (
    cache_key,
    deserialize_agent,
    serialize_agent,
)
from nl_engine.benchmarks.schema import Question
from nl_engine.types.answer import AnswerResponse, ClarificationResponse

AGENT_PATH = "agent"


def agent_to_grader_inputs(
    agent_result: AgentEvalResult,
) -> tuple[AnswerResponse | ClarificationResponse, list[dict[str, Any]]]:
    """Bridge AgentEvalResult into the (result, trace) shape grade() expects."""
    if agent_result.final_message_kind == "clarify":
        return (
            ClarificationResponse(question=agent_result.summary or "..."),
            agent_result.tool_call_trace,
        )
    return (
        AnswerResponse(
            sql="<agent>",  # non-empty placeholder so sql_valid passes
            explanation=agent_result.summary,
            tables_used=[],
            assumptions=[],
            caveats=[],
            rows=agent_result.rows,
            columns=agent_result.columns,
        ),
        agent_result.tool_call_trace,
    )


def agent_path_meaningful(q: Question) -> bool:
    """Skip long-tail agent grading (HUG-189 Option B).

    Row-set match requires `ground_truth_rows`; the structural fallback
    (table_equivalence + keyword_frac) doesn't fit the agent's output
    shape (no SQL string, no real tables_used). Long-tail agent grading
    is reported as informational only via the ledger column.
    """
    return q.ground_truth_rows is not None or q.question_type == "ambiguous"


def run_agent(
    q: Question,
    db_url: str,
    llm: BaseChatModel,
    cache: dict[str, dict[str, object]],
) -> AgentEvalResult:
    key = cache_key(q.question, db_url, AGENT_PATH)
    # EVAL_TRACE=1 bypasses the cache so the ReAct trace prints fresh —
    # cached results skip the agent invocation entirely (no trace to dump).
    if key in cache and os.environ.get("EVAL_TRACE") != "1":
        return deserialize_agent(cache[key])
    try:
        result = run_agent_question(q.question, db_url, llm)
    except Exception as exc:  # noqa: BLE001
        result = AgentEvalResult(
            summary=f"agent error: {exc}",
            final_message_kind="unknown",
        )
    cache[key] = serialize_agent(result)
    return result


__all__ = [
    "AGENT_PATH",
    "Path",
    "agent_path_meaningful",
    "agent_to_grader_inputs",
    "run_agent",
]
