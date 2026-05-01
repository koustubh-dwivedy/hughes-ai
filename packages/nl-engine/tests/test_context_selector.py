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


# ---- total deposits ----

def test_deposit_balance_table(selector: ContextSelector) -> None:
    sc = selector.select("What is our total deposit balance this month?")
    assert "fct_deposits_monthly" in _tables(sc)


def test_deposit_balance_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is our total deposit balance this month?")
    assert "total_deposits" in _metrics(sc)


def test_deposit_product_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is the deposit breakdown by product type?")
    assert "deposits_by_product" in _metrics(sc)


# ---- top depositors ----

def test_top_depositor_table(selector: ContextSelector) -> None:
    sc = selector.select("Who are our top 25 depositors?")
    assert "dim_member" in _tables(sc)


def test_top_depositor_metric(selector: ContextSelector) -> None:
    sc = selector.select("Who are our top depositors?")
    assert "top_n_deposits" in _metrics(sc)


# ---- officer portfolio ----

def test_officer_table(selector: ContextSelector) -> None:
    sc = selector.select("Which officers have the most past-due exposure?")
    assert "dim_officer" in _tables(sc)


def test_officer_column(selector: ContextSelector) -> None:
    sc = selector.select("Which loan officer has the highest delinquency?")
    assert "officer_name" in _cols(sc)


# ---- watchlist / risk ----

def test_watchlist_metric(selector: ContextSelector) -> None:
    sc = selector.select("How many loans are on the watchlist?")
    assert "watchlist_count" in _metrics(sc)


def test_nonaccrual_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is our nonaccrual balance?")
    assert "nonaccrual_balance" in _metrics(sc)


def test_npl_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is our NPL balance?")
    assert "nonperforming_loan_balance" in _metrics(sc)


def test_aging_bucket_column(selector: ContextSelector) -> None:
    sc = selector.select("Show delinquency aging bucket breakdown")
    assert "bucket" in _cols(sc)


# ---- executive KPIs ----

def test_ltd_ratio_table(selector: ContextSelector) -> None:
    sc = selector.select("What is our loan-to-deposit ratio?")
    assert "fct_executive_kpis" in _tables(sc)


def test_ltd_ratio_metric(selector: ContextSelector) -> None:
    sc = selector.select("Show loan to deposit ratio trend")
    assert "loan_to_deposit_ratio" in _metrics(sc)


def test_core_deposit_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is our core deposit ratio?")
    assert "core_deposit_ratio" in _metrics(sc)


def test_rate_spread_metric(selector: ContextSelector) -> None:
    sc = selector.select("How has our rate spread changed over the year?")
    assert "rate_spread" in _metrics(sc)


# ---- MTD / YTD ----

def test_mtd_table(selector: ContextSelector) -> None:
    sc = selector.select("What is the MTD deposit change?")
    assert "fct_deposits_monthly" in _tables(sc)


def test_mtd_metric(selector: ContextSelector) -> None:
    sc = selector.select("Show MTD deposit change by branch")
    assert "mtd_deposit_change" in _metrics(sc)


def test_ytd_metric(selector: ContextSelector) -> None:
    sc = selector.select("What is the year-to-date deposit growth?")
    assert "ytd_deposit_change" in _metrics(sc)


def test_monthly_growth_metric(selector: ContextSelector) -> None:
    sc = selector.select("Show monthly loan growth for the last 12 months")
    assert "monthly_growth_loans" in _metrics(sc)


# ---- top borrowers / single-loan ----

def test_top_borrower_table(selector: ContextSelector) -> None:
    sc = selector.select("Who are our top 25 borrowers?")
    assert "fct_loans_monthly" in _tables(sc)


def test_top_borrower_metric(selector: ContextSelector) -> None:
    sc = selector.select("Show the top 10 borrowers by outstanding balance")
    assert "top_n_borrowers" in _metrics(sc)


def test_single_loan_metric(selector: ContextSelector) -> None:
    sc = selector.select("How many single-loan customers do we have?")
    assert "single_loan_customers" in _metrics(sc)


# ---- loan lifecycle ----

def test_lifecycle_table(selector: ContextSelector) -> None:
    sc = selector.select("Show new and paid-off loan lifecycle events")
    assert "fct_loan_lifecycle_events" in _tables(sc)
