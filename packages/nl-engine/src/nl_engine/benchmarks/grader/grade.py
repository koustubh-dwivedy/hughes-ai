"""Top-level grader entry point — `grade()` and `GradeResult`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nl_engine.benchmarks.grader.categorize import (
    CategoryOutcome,
    categorize,
)
from nl_engine.benchmarks.grader.match import (
    KEYWORD_FRAC_THRESHOLD,
    TABLE_EQUIV_THRESHOLD,
    columnset_match,
    keyword_frac,
    rowset_match,
    table_equivalence,
)
from nl_engine.benchmarks.schema import Question, QuestionType
from nl_engine.engine import AnswerResponse, ClarificationResponse


@dataclass
class GradeResult:
    question_id: str | None
    question: str
    question_type: QuestionType
    must_pass: bool
    correct: bool
    category: CategoryOutcome
    sql_valid: bool | None = None
    table_equivalence: float | None = None
    keyword_frac: float | None = None
    rowset_diff: str = ""
    columnset_diff: str = ""


def _grade_clarification(
    question: Question,
    result: ClarificationResponse,
    tool_call_trace: list[dict[str, Any]] | None,
) -> GradeResult:
    category = categorize(question, result, tool_call_trace=tool_call_trace)
    return GradeResult(
        question_id=question.id,
        question=question.question,
        question_type=question.question_type,
        must_pass=question.must_pass,
        correct=category == "clarification_correct",
        category=category,
    )


def _grade_with_ground_truth(
    question: Question,
    result: AnswerResponse,
    sql_valid: bool,
    tool_call_trace: list[dict[str, Any]] | None,
) -> GradeResult:
    gt_rows = question.ground_truth_rows or []
    rows_ok, rows_diff = rowset_match(gt_rows, result.rows)
    cols_expected = list(gt_rows[0].keys()) if gt_rows else []
    cols_ok, cols_diff = columnset_match(cols_expected, result.columns)
    if not sql_valid:
        return GradeResult(
            question_id=question.id,
            question=question.question,
            question_type=question.question_type,
            must_pass=question.must_pass,
            correct=False,
            category="parse_error",
            sql_valid=False,
        )
    category = categorize(
        question,
        result,
        rowset_ok=rows_ok,
        columnset_ok=cols_ok,
        tool_call_trace=tool_call_trace,
    )
    return GradeResult(
        question_id=question.id,
        question=question.question,
        question_type=question.question_type,
        must_pass=question.must_pass,
        correct=rows_ok and cols_ok,
        category=category,
        sql_valid=sql_valid,
        rowset_diff=rows_diff,
        columnset_diff=cols_diff,
    )


def _grade_structural(
    question: Question,
    result: AnswerResponse,
    sql: str,
    sql_valid: bool,
    tool_call_trace: list[dict[str, Any]] | None,
) -> GradeResult:
    actual_tables = list(result.tables_used or [])
    table_eq = table_equivalence(
        question.expected_tables,
        actual_tables,
        question.equivalent_tables,
    )
    kw = keyword_frac(question.expected_keywords, sql)
    correct = (
        sql_valid
        and table_eq >= TABLE_EQUIV_THRESHOLD
        and kw >= KEYWORD_FRAC_THRESHOLD
    )
    category = categorize(
        question,
        result,
        table_equiv=table_eq,
        kw_frac=kw,
        tool_call_trace=tool_call_trace,
    )
    return GradeResult(
        question_id=question.id,
        question=question.question,
        question_type=question.question_type,
        must_pass=question.must_pass,
        correct=correct,
        category=category,
        sql_valid=sql_valid,
        table_equivalence=round(table_eq, 3),
        keyword_frac=round(kw, 3),
    )


def grade(
    question: Question,
    result: AnswerResponse | ClarificationResponse,
    tool_call_trace: list[dict[str, Any]] | None = None,
) -> GradeResult:
    """Run the full grader for one question. Top-level entry point."""
    if isinstance(result, ClarificationResponse):
        return _grade_clarification(question, result, tool_call_trace)
    sql = result.sql or ""
    sql_valid = bool(sql.strip())
    if question.ground_truth_rows is not None:
        return _grade_with_ground_truth(
            question, result, sql_valid, tool_call_trace
        )
    return _grade_structural(question, result, sql, sql_valid, tool_call_trace)
