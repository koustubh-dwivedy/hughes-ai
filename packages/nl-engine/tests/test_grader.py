"""Unit tests for the grader categorizer, top-level grade(), and gate (HUG-188)."""

from __future__ import annotations

import pytest
from nl_engine.benchmarks.grader import (
    GradeResult,
    categorize,
    evaluate_gate,
    grade,
    parse_gate_arg,
)
from nl_engine.benchmarks.schema import Question
from nl_engine.engine import AnswerResponse, ClarificationResponse


def _q(**kw: object) -> Question:
    base: dict[str, object] = {
        "question": "test?",
        "question_type": "origination_volume",
    }
    base.update(kw)
    return Question.model_validate(base)


def _ans(
    sql: str = "SELECT 1",
    rows: list[dict[str, object]] | None = None,
    columns: list[str] | None = None,
    tables_used: list[str] | None = None,
) -> AnswerResponse:
    return AnswerResponse(
        sql=sql,
        explanation="",
        tables_used=tables_used or [],
        assumptions=[],
        caveats=[],
        rows=rows or [],
        columns=columns or [],
    )


def _gr(must_pass: bool, correct: bool, category: str = "ok") -> GradeResult:
    return GradeResult(
        question_id=None,
        question="q",
        question_type="origination_volume",
        must_pass=must_pass,
        correct=correct,
        category=category,  # type: ignore[arg-type]
    )


# ── categorize ───────────────────────────────────────────────────────────────


def test_categorize_clarification_on_ambiguous_is_correct() -> None:
    q = _q(question_type="ambiguous")
    cat = categorize(q, ClarificationResponse(question="which?"))
    assert cat == "clarification_correct"


def test_categorize_clarification_on_non_ambiguous_is_missed() -> None:
    cat = categorize(_q(), ClarificationResponse(question="?"))
    assert cat == "clarification_missed"


def test_categorize_mf_unsupported_via_trace() -> None:
    trace = [{"tool": "list_metrics"}, {"tool": "clarify"}]
    cat = categorize(
        _q(),
        ClarificationResponse(question="No metric covers this data."),
        tool_call_trace=trace,
    )
    assert cat == "mf_unsupported"


def test_categorize_mf_unsupported_skipped_when_mf_query_called() -> None:
    trace = [
        {"tool": "list_metrics"},
        {"tool": "mf_query"},
        {"tool": "clarify"},
    ]
    cat = categorize(
        _q(),
        ClarificationResponse(question="metric not found"),
        tool_call_trace=trace,
    )
    assert cat == "clarification_missed"


def test_categorize_empty_sql_is_parse_error() -> None:
    cat = categorize(_q(), _ans(sql=""))
    assert cat == "parse_error"


def test_categorize_no_rows_with_ground_truth() -> None:
    q = _q(ground_truth_rows=[{"x": 1}])
    cat = categorize(q, _ans(sql="SELECT", rows=[]))
    assert cat == "no_rows"


def test_categorize_wrong_columns_with_ground_truth() -> None:
    q = _q(ground_truth_rows=[{"x": 1}])
    cat = categorize(q, _ans(rows=[{"y": 1}], columns=["y"]), columnset_ok=False)
    assert cat == "wrong_columns"


def test_categorize_wrong_rows_with_ground_truth() -> None:
    q = _q(ground_truth_rows=[{"x": 1}])
    cat = categorize(
        q, _ans(rows=[{"x": 99}], columns=["x"]),
        rowset_ok=False, columnset_ok=True,
    )
    assert cat == "wrong_rows"


def test_categorize_ok_with_ground_truth() -> None:
    q = _q(ground_truth_rows=[{"x": 1}])
    cat = categorize(
        q, _ans(rows=[{"x": 1}], columns=["x"]),
        rowset_ok=True, columnset_ok=True,
    )
    assert cat == "ok"


def test_categorize_missing_table_in_fallback() -> None:
    cat = categorize(_q(), _ans(), table_equiv=0.5, kw_frac=1.0)
    assert cat == "missing_table"


def test_categorize_sql_error_in_fallback() -> None:
    cat = categorize(_q(), _ans(), table_equiv=1.0, kw_frac=0.3)
    assert cat == "sql_error"


def test_categorize_ok_in_fallback() -> None:
    cat = categorize(_q(), _ans(), table_equiv=1.0, kw_frac=1.0)
    assert cat == "ok"


# ── grade (top-level) ────────────────────────────────────────────────────────


def test_grade_ambiguous_clarification_is_correct() -> None:
    q = _q(question_type="ambiguous")
    r = grade(q, ClarificationResponse(question="?"))
    assert r.correct and r.category == "clarification_correct"


def test_grade_clarification_on_non_ambiguous_is_incorrect() -> None:
    r = grade(_q(), ClarificationResponse(question="?"))
    assert not r.correct and r.category == "clarification_missed"


def test_grade_must_pass_with_correct_rows() -> None:
    q = _q(must_pass=True, ground_truth_rows=[{"x": 1}])
    r = grade(q, _ans(sql="SELECT", rows=[{"x": 1}], columns=["x"]))
    assert r.correct and r.category == "ok" and r.must_pass


def test_grade_must_pass_with_wrong_rows() -> None:
    q = _q(must_pass=True, ground_truth_rows=[{"x": 1}])
    r = grade(q, _ans(sql="SELECT", rows=[{"x": 99}], columns=["x"]))
    assert not r.correct and r.category == "wrong_rows"
    assert "expected=1" in r.rowset_diff


def test_grade_long_tail_structural_pass() -> None:
    q = _q(
        expected_tables=["fct_loan_originations"],
        expected_keywords=["COUNT", "funded_at"],
    )
    r = grade(
        q,
        _ans(
            sql="SELECT COUNT(*) FROM fct_loan_originations WHERE funded_at > X",
            tables_used=["fct_loan_originations"],
        ),
    )
    assert r.correct and r.category == "ok"
    assert r.table_equivalence == 1.0
    assert r.keyword_frac == 1.0


def test_grade_long_tail_structural_fail_table() -> None:
    q = _q(expected_tables=["fct_a", "fct_b"], expected_keywords=[])
    r = grade(q, _ans(sql="SELECT 1", tables_used=["fct_c"]))
    assert not r.correct and r.category == "missing_table"


def test_grade_empty_sql_is_parse_error() -> None:
    q = _q(ground_truth_rows=[{"x": 1}])
    r = grade(q, _ans(sql="", rows=[]))
    assert not r.correct and r.category == "parse_error"


def test_grade_with_equivalent_tables_collapses() -> None:
    q = _q(
        expected_tables=["fct_deposits_monthly"],
        expected_keywords=[],
        equivalent_tables=[["fct_deposits_monthly", "deposit_accounts"]],
    )
    r = grade(q, _ans(sql="SELECT 1", tables_used=["deposit_accounts"]))
    assert r.correct
    assert r.table_equivalence == 1.0


# ── parse_gate_arg ───────────────────────────────────────────────────────────


def test_parse_gate_arg_basic() -> None:
    assert parse_gate_arg("must-pass=80,long-tail=65") == {
        "must-pass": 80.0,
        "long-tail": 65.0,
    }


def test_parse_gate_arg_whitespace() -> None:
    assert parse_gate_arg(" must-pass = 80 , long-tail = 65 ") == {
        "must-pass": 80.0,
        "long-tail": 65.0,
    }


def test_parse_gate_arg_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_gate_arg("")


def test_parse_gate_arg_missing_equals_raises() -> None:
    with pytest.raises(ValueError):
        parse_gate_arg("must-pass80")


def test_parse_gate_arg_non_numeric_raises() -> None:
    with pytest.raises(ValueError):
        parse_gate_arg("must-pass=high")


# ── evaluate_gate ────────────────────────────────────────────────────────────


def test_evaluate_gate_must_pass_meets_threshold() -> None:
    results = [_gr(True, True), _gr(True, True), _gr(True, False)]
    code, tiers = evaluate_gate(results, {"must-pass": 50.0, "long-tail": 65.0})
    mp = next(t for t in tiers if t.name == "must-pass")
    assert code == 0 and mp.status == "PASS" and mp.accuracy == pytest.approx(66.7)


def test_evaluate_gate_must_pass_below_threshold_fails() -> None:
    results = [_gr(True, False), _gr(True, False), _gr(True, True)]
    code, tiers = evaluate_gate(results, {"must-pass": 80.0, "long-tail": 65.0})
    mp = next(t for t in tiers if t.name == "must-pass")
    assert code == 1 and mp.status == "FAIL"


def test_evaluate_gate_long_tail_below_threshold_warns() -> None:
    results = [_gr(False, False), _gr(False, False), _gr(False, True)]
    code, tiers = evaluate_gate(results, {"must-pass": 80.0, "long-tail": 65.0})
    lt = next(t for t in tiers if t.name == "long-tail")
    assert code == 0 and lt.status == "WARN"


def test_evaluate_gate_empty_must_pass_passes() -> None:
    """User-decided 2026-05-05: empty must-pass tier must not block."""
    results = [_gr(False, True), _gr(False, False)]
    code, tiers = evaluate_gate(results, {"must-pass": 80.0, "long-tail": 65.0})
    mp = next(t for t in tiers if t.name == "must-pass")
    assert code == 0 and mp.status == "EMPTY" and mp.total == 0


def test_evaluate_gate_failures_by_category_populated() -> None:
    results = [
        _gr(True, False, "wrong_rows"),
        _gr(True, False, "wrong_rows"),
        _gr(True, False, "no_rows"),
    ]
    _, tiers = evaluate_gate(results, {"must-pass": 80.0})
    mp = next(t for t in tiers if t.name == "must-pass")
    assert mp.failures_by_category == {"wrong_rows": 2, "no_rows": 1}
