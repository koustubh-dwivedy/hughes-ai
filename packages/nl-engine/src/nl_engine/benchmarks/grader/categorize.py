"""Categorize a question's outcome (parse_error / wrong_rows / mf_unsupported / ...)."""

from __future__ import annotations

from typing import Any, Literal

from nl_engine.benchmarks.grader.match import (
    KEYWORD_FRAC_THRESHOLD,
    TABLE_EQUIV_THRESHOLD,
)
from nl_engine.benchmarks.schema import Question
from nl_engine.types.answer import AnswerResponse, ClarificationResponse

CategoryOutcome = Literal[
    "ok",
    "parse_error",
    "sql_error",
    "no_rows",
    "wrong_rows",
    "wrong_columns",
    "missing_table",
    "clarification_missed",
    "clarification_correct",
    "mf_unsupported",
]


def _detect_mf_unsupported(
    trace: list[dict[str, Any]] | None,
    clarify_message: str,
) -> bool:
    """Heuristic: agent looked up metrics, never queried, ended in clarify."""
    if not trace:
        return False
    called_lookup = any(
        t.get("tool") in {"list_metrics", "lookup_metric_definition"} for t in trace
    )
    called_query = any(t.get("tool") == "mf_query" for t in trace)
    if not called_lookup or called_query:
        return False
    body = clarify_message.lower()
    return "metric" in body or "data not available" in body


def _categorize_clarification(
    question: Question,
    result: ClarificationResponse,
    tool_call_trace: list[dict[str, Any]] | None,
) -> CategoryOutcome:
    if question.question_type == "ambiguous":
        return "clarification_correct"
    if _detect_mf_unsupported(tool_call_trace, result.question):
        return "mf_unsupported"
    return "clarification_missed"


def _categorize_answer_with_ground_truth(
    result: AnswerResponse,
    rowset_ok: bool | None,
    columnset_ok: bool | None,
) -> CategoryOutcome:
    if not result.rows:
        return "no_rows"
    if columnset_ok is False:
        return "wrong_columns"
    if rowset_ok is False:
        return "wrong_rows"
    return "ok"


def _categorize_answer_structural(
    table_equiv: float | None,
    kw_frac: float | None,
) -> CategoryOutcome:
    if table_equiv is not None and table_equiv < TABLE_EQUIV_THRESHOLD:
        return "missing_table"
    if kw_frac is not None and kw_frac < KEYWORD_FRAC_THRESHOLD:
        return "sql_error"
    return "ok"


def categorize(
    question: Question,
    result: AnswerResponse | ClarificationResponse,
    rowset_ok: bool | None = None,
    columnset_ok: bool | None = None,
    table_equiv: float | None = None,
    kw_frac: float | None = None,
    tool_call_trace: list[dict[str, Any]] | None = None,
) -> CategoryOutcome:
    """Return the categorized outcome for a question + result pair.

    Pre-computed grader signals (rowset_ok, columnset_ok, table_equiv,
    kw_frac) are passed in to avoid duplicate work — they are computed once
    in `grade()` and reused here.

    `tool_call_trace` enables `mf_unsupported` detection. Surface 1's
    `engine.ask` does not produce a trace; pass None and the heuristic
    falls through to `clarification_missed`.
    """
    if isinstance(result, ClarificationResponse):
        return _categorize_clarification(question, result, tool_call_trace)
    if not result.sql.strip():
        return "parse_error"
    if question.ground_truth_rows is not None:
        return _categorize_answer_with_ground_truth(
            result, rowset_ok, columnset_ok
        )
    return _categorize_answer_structural(table_equiv, kw_frac)
