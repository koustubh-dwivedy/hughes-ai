"""Reconciliation: every metric MetricFlow returns matches the corresponding
mart aggregate within $1 (HUG-174).

This is the hard accuracy gate that proves the semantic-layer translation
preserves the same numbers as the existing dashboards. Failure = bug
in the MetricFlow translation, not an acceptable drift.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from nl_engine.repo import metricflow as mf

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_TOLERANCE_DOLLARS = 1.0


def _db() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set; reconciliation needs Postgres")
    return psycopg.connect(url, autocommit=True)


def _scalar(conn: psycopg.Connection, sql: str) -> float:
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return float(row[0] or 0)


def _mf_total(metric: str) -> float:
    """Sum across the time grain to get a portfolio-wide total."""
    result = mf.query(metric, dimensions=["metric_time__month"])
    if not result.rows:
        return 0.0
    # The metric column is named after the metric.
    total = 0.0
    for row in result.rows:
        val = row.get(metric)
        if val in (None, ""):
            continue
        total += float(val)
    return total


def _mf_latest(metric: str) -> float:
    """Get the latest-month value for portfolio-state metrics
    (loans/deposits balances, ratios, etc.)."""
    result = mf.query(
        metric,
        dimensions=["metric_time__month"],
        order="-metric_time__month",
        limit=1,
    )
    if not result.rows:
        return 0.0
    val = result.rows[0].get(metric)
    return float(val) if val not in (None, "") else 0.0


def test_total_loan_balance_reconciles_to_mart() -> None:
    """MetricFlow's total_loan_balance (latest month) ≈ fct_loans_monthly latest sum.

    Metric renamed in catalog overhaul 2026-05-10b (HUG-193) for
    self-disambiguation; was `total_loans`."""
    with _db() as conn:
        mart_total = _scalar(
            conn,
            "SELECT COALESCE(SUM(total_balance), 0) FROM fct_loans_monthly"
            " WHERE as_of_month = (SELECT MAX(as_of_month) FROM fct_loans_monthly)",
        )
    mf_total = _mf_latest("total_loan_balance")
    assert abs(mart_total - mf_total) < _TOLERANCE_DOLLARS, (
        f"total_loan_balance drift: mart={mart_total:,.2f} vs mf={mf_total:,.2f}"
    )


def test_total_deposit_balance_reconciles_to_mart() -> None:
    with _db() as conn:
        mart_total = _scalar(
            conn,
            "SELECT COALESCE(SUM(total_balance), 0) FROM fct_deposits_monthly"
            " WHERE as_of_month = (SELECT MAX(as_of_month) FROM fct_deposits_monthly)",
        )
    mf_total = _mf_latest("total_deposit_balance")
    assert abs(mart_total - mf_total) < _TOLERANCE_DOLLARS, (
        f"total_deposit_balance drift: mart={mart_total:,.2f} vs mf={mf_total:,.2f}"
    )


def test_loan_to_deposit_ratio_reconciles_to_kpi_mart() -> None:
    with _db() as conn:
        mart_value = _scalar(
            conn,
            "SELECT loan_to_deposit_ratio FROM fct_executive_kpis"
            " WHERE as_of_month = (SELECT MAX(as_of_month) FROM fct_executive_kpis)",
        )
    mf_value = _mf_latest("loan_to_deposit_ratio")
    # Ratios — tolerance 0.0001 (4 decimal places).
    assert abs(mart_value - mf_value) < 0.0001, (
        f"loan_to_deposit_ratio drift: mart={mart_value} vs mf={mf_value}"
    )


def test_core_deposit_ratio_reconciles_to_kpi_mart() -> None:
    with _db() as conn:
        mart_value = _scalar(
            conn,
            "SELECT core_deposit_ratio FROM fct_executive_kpis"
            " WHERE as_of_month = (SELECT MAX(as_of_month) FROM fct_executive_kpis)",
        )
    mf_value = _mf_latest("core_deposit_ratio")
    assert abs(mart_value - mf_value) < 0.0001, (
        f"core_deposit_ratio drift: mart={mart_value} vs mf={mf_value}"
    )


def test_rate_spread_reconciles_to_kpi_mart() -> None:
    with _db() as conn:
        mart_value = _scalar(
            conn,
            "SELECT rate_spread FROM fct_executive_kpis"
            " WHERE as_of_month = (SELECT MAX(as_of_month) FROM fct_executive_kpis)",
        )
    mf_value = _mf_latest("rate_spread")
    assert abs(mart_value - mf_value) < 0.0001, (
        f"rate_spread drift: mart={mart_value} vs mf={mf_value}"
    )


def test_cecl_allowance_balance_reconciles() -> None:
    with _db() as conn:
        mart_total = _scalar(
            conn,
            "SELECT COALESCE(SUM(ending_balance), 0)"
            " FROM fct_cecl_allowance_rollforward"
            " WHERE period_end_month ="
            " (SELECT MAX(period_end_month) FROM fct_cecl_allowance_rollforward)",
        )
    mf_total = _mf_latest("cecl_allowance_balance")
    assert abs(mart_total - mf_total) < _TOLERANCE_DOLLARS, (
        f"cecl_allowance_balance drift: mart={mart_total:,.2f} vs mf={mf_total:,.2f}"
    )


def test_mf_list_returns_all_metrics() -> None:
    """Smoke test: `mf list metrics` parses + returns the 38 expected metrics."""
    metrics = mf.list_metrics()
    names = {m.name for m in metrics}
    # Spot-check a representative sample
    expected = {
        "total_loan_balance", "total_deposit_balance", "delinquency_rate",
        "loan_to_deposit_ratio", "cecl_allowance_balance",
        "ncua_total_loans", "approval_rate", "rate_spread",
    }
    missing = expected - names
    assert not missing, f"mf list missing: {missing}"
