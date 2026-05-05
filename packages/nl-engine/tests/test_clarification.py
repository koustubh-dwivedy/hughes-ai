"""Tests for HUG-29: ambiguity detection and metric caveat injection."""

import pytest
from nl_engine.context_loader import AllContext, Column, Metric, Rule, Table
from nl_engine.context_selector import SelectedContext
from nl_engine.engine import (
    AnswerResponse,
    ClarificationResponse,
    _ambiguity_clarification,
    _inject_metric_caveats,
    _is_ambiguous,
    ask,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _col(name: str) -> Column:
    return Column(name=name, type="TEXT", description="", example="")


def _metric(name: str, label: str, caveat: str = "Watch out.") -> Metric:
    return Metric(
        name=name,
        label=label,
        description="",
        formula_plain_english="",
        caveats=caveat,
        related_questions=[],
    )


def _table(name: str, *cols: str) -> Table:
    return Table(name=name, description="", columns=[_col(c) for c in cols])


def _ctx_with_metrics(*metrics: Metric) -> SelectedContext:
    table = _table("fct_loan_originations", "loan_id", "funded_at", "loan_status")
    return SelectedContext(
        relevant_tables=[table],
        relevant_metrics=list(metrics),
        relevant_columns=table.columns,
        relevant_examples=[],
    )


def _make_full_ctx(metrics: list[Metric]) -> AllContext:
    table = _table("fct_loan_originations", "loan_id", "funded_at", "loan_status")
    rule = Rule(id="r1", rule="Use funded_at", rationale="Standard")
    return AllContext(
        tables=[table], metrics=metrics, rules=[rule], examples=[]
    )


# ---------------------------------------------------------------------------
# Ambiguity detection
# ---------------------------------------------------------------------------


def test_two_metrics_is_ambiguous() -> None:
    m1 = _metric("approval_rate", "Approval Rate")
    m2 = _metric("delinquency_rate", "Delinquency Rate")
    assert _is_ambiguous(_ctx_with_metrics(m1, m2))


def test_one_metric_not_ambiguous() -> None:
    m = _metric("approval_rate", "Approval Rate")
    assert not _is_ambiguous(_ctx_with_metrics(m))


def test_zero_metrics_not_ambiguous() -> None:
    assert not _is_ambiguous(_ctx_with_metrics())


def test_ambiguity_clarification_names_metrics() -> None:
    m1 = _metric("approval_rate", "Approval Rate")
    m2 = _metric("funding_rate", "Funding Rate")
    result = _ambiguity_clarification(_ctx_with_metrics(m1, m2))
    assert isinstance(result, ClarificationResponse)
    assert "Approval Rate" in result.question
    assert "Funding Rate" in result.question


# ---------------------------------------------------------------------------
# ask() ambiguity path — real ContextSelector with 2 matched metrics
# ---------------------------------------------------------------------------


def test_ask_ambiguous_question_returns_clarification() -> None:
    m_approval = _metric("approval_rate", "Approval Rate", "Exclude pending.")
    m_delinquency = _metric("delinquency_rate", "Delinquency Rate", "30+ DPD only.")
    ctx = _make_full_ctx([m_approval, m_delinquency])

    result = ask(
        "What's our approval and delinquency rate?",
        "postgresql://localhost/cubi",
        ctx,
    )

    assert isinstance(result, ClarificationResponse)
    assert "Approval Rate" in result.question
    assert "Delinquency Rate" in result.question


def test_ask_vague_question_returns_clarification() -> None:
    ctx = _make_full_ctx([_metric("approval_rate", "Approval Rate")])
    result = ask("Show me the rate", "postgresql://localhost/cubi", ctx)
    assert isinstance(result, ClarificationResponse)


# ---------------------------------------------------------------------------
# Caveat injection
# ---------------------------------------------------------------------------


def test_metric_caveats_injected_into_answer() -> None:
    m = _metric("approval_rate", "Approval Rate", "Exclude pending decisions.")
    selected = _ctx_with_metrics(m)
    answer = AnswerResponse(
        sql="SELECT 1",
        explanation="",
        tables_used=[],
        assumptions=[],
        caveats=[],
        rows=[],
        columns=[],
    )
    result = _inject_metric_caveats(answer, selected)
    assert "Exclude pending decisions." in result.caveats


def test_caveat_not_duplicated_if_already_present() -> None:
    m = _metric("approval_rate", "Approval Rate", "Exclude pending.")
    selected = _ctx_with_metrics(m)
    answer = AnswerResponse(
        sql="SELECT 1",
        explanation="",
        tables_used=[],
        assumptions=[],
        caveats=["Exclude pending."],
        rows=[],
        columns=[],
    )
    result = _inject_metric_caveats(answer, selected)
    assert result.caveats.count("Exclude pending.") == 1


def test_multiple_metric_caveats_all_injected() -> None:
    m1 = _metric("approval_rate", "Approval Rate", "Caveat A.")
    m2 = _metric("funding_rate", "Funding Rate", "Caveat B.")
    selected = _ctx_with_metrics(m1, m2)
    answer = AnswerResponse(
        sql="SELECT 1",
        explanation="",
        tables_used=[],
        assumptions=[],
        caveats=[],
        rows=[],
        columns=[],
    )
    result = _inject_metric_caveats(answer, selected)
    assert "Caveat A." in result.caveats
    assert "Caveat B." in result.caveats


def test_caveats_injected_in_full_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    m = _metric("approval_rate", "Approval Rate", "Exclude pending decisions.")
    ctx = _make_full_ctx([m])
    valid_sql = "SELECT loan_id FROM fct_loan_originations"

    monkeypatch.setattr(
        "nl_engine.engine._call_llm",
        lambda *_a, **_kw: (
            {
                "sql": valid_sql,
                "explanation": "ok",
                "tables_used": ["fct_loan_originations"],
                "assumptions": [],
                "caveats": [],
            },
            42,
            "qwen/qwen3-32b",
        ),
    )
    monkeypatch.setattr(
        "nl_engine.engine.execute_sql", lambda *_a, **_kw: ([], [])
    )

    result = ask("What is the approval rate?", "postgresql://localhost/cubi", ctx)

    assert isinstance(result, AnswerResponse)
    assert "Exclude pending decisions." in result.caveats
