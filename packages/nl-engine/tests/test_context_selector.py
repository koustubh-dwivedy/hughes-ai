"""Routing assertions for ContextSelector keyword matching."""

import pytest
from nl_engine.context_loader import load_all
from nl_engine.context_selector import ContextSelector, SelectedContext


@pytest.fixture(scope="module")
def selector() -> ContextSelector:
    return ContextSelector(load_all())


def _tables(sc: SelectedContext) -> list[str]:
    return [t.name for t in sc.relevant_tables]


def _metrics(sc: SelectedContext) -> list[str]:
    return [m.name for m in sc.relevant_metrics]


def _cols(sc: SelectedContext) -> list[str]:
    return [c.name for c in sc.relevant_columns]


# ---- approval rate by branch ----

def test_approval_rate_branch_metric(selector: ContextSelector) -> None:
    sc = selector.select("What was the approval rate by branch?")
    assert "approval_rate" in _metrics(sc)


def test_approval_rate_branch_table(selector: ContextSelector) -> None:
    sc = selector.select("What was the approval rate by branch?")
    assert "fct_loan_originations" in _tables(sc)


def test_approval_rate_branch_column(selector: ContextSelector) -> None:
    sc = selector.select("What was the approval rate by branch?")
    assert "branch_name" in _cols(sc)


# ---- delinquency trend ----

def test_delinquency_trend_metric(selector: ContextSelector) -> None:
    sc = selector.select("Show delinquency trend last 6 months")
    assert "delinquency_rate" in _metrics(sc)


def test_delinquency_trend_table(selector: ContextSelector) -> None:
    sc = selector.select("Show delinquency trend last 6 months")
    assert "fct_loan_performance" in _tables(sc)


def test_delinquency_trend_dpd_column(selector: ContextSelector) -> None:
    sc = selector.select("Show delinquency trend last 6 months")
    assert "days_past_due" in _cols(sc)


# ---- out of scope: members ----

def test_out_of_scope_no_tables(selector: ContextSelector) -> None:
    sc = selector.select("Tell me about our members")
    assert sc.relevant_tables == []


def test_out_of_scope_no_metrics(selector: ContextSelector) -> None:
    sc = selector.select("Tell me about our members")
    assert sc.relevant_metrics == []


def test_out_of_scope_no_columns(selector: ContextSelector) -> None:
    sc = selector.select("Tell me about our members")
    assert sc.relevant_columns == []


def test_out_of_scope_no_examples(selector: ContextSelector) -> None:
    sc = selector.select("Tell me about our members")
    assert sc.relevant_examples == []


# ---- portfolio balance ----

def test_portfolio_balance_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is our total portfolio balance today?")
    assert "portfolio_balance" in _metrics(sc)


def test_portfolio_balance_table(selector: ContextSelector) -> None:
    sc = selector.select("What is our total portfolio balance today?")
    assert "fct_loan_performance" in _tables(sc)


# ---- origination volume ----

def test_origination_volume_metric(selector: ContextSelector) -> None:
    sc = selector.select("How many loans did we originate last month?")
    assert "origination_volume" in _metrics(sc)


def test_origination_volume_table(selector: ContextSelector) -> None:
    sc = selector.select("How many loans did we originate last month?")
    assert "fct_loan_originations" in _tables(sc)


# ---- average loan amount ----

def test_avg_loan_amount_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is the average loan amount this year?")
    assert "avg_loan_amount" in _metrics(sc)


def test_avg_loan_amount_by_branch_columns(selector: ContextSelector) -> None:
    sc = selector.select("What is the average loan amount by branch?")
    assert "branch_name" in _cols(sc)
    assert "avg_loan_amount" in _metrics(sc)


# ---- channel breakdown ----

def test_channel_column_present(selector: ContextSelector) -> None:
    sc = selector.select("Show origination volume by channel")
    assert "channel" in _cols(sc)


# ---- product type ----

def test_product_type_column(selector: ContextSelector) -> None:
    sc = selector.select("Delinquency rate by product type")
    assert "product_type" in _cols(sc)


# ---- reconciliation ----

def test_recon_bridge_table(selector: ContextSelector) -> None:
    sc = selector.select("What is our LOS match rate from the reconciliation?")
    assert "recon_bridge" in _tables(sc)


# ---- funded loans ----

def test_funded_loans_table(selector: ContextSelector) -> None:
    sc = selector.select("How many loans were funded this year?")
    assert "fct_loan_originations" in _tables(sc)


# ---- funding rate ----

def test_funding_rate_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is our funding rate this quarter?")
    assert "funding_rate" in _metrics(sc)


# ---- 30 days past due ----

def test_30_day_dpd_metric(selector: ContextSelector) -> None:
    sc = selector.select("How many loans are 30 day past due?")
    assert "delinquency_rate" in _metrics(sc)


# ---- robustness ----

def test_empty_question_no_crash(selector: ContextSelector) -> None:
    sc = selector.select("")
    assert sc.relevant_tables == []
