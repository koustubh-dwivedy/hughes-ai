"""Read-only access helpers for executive KPI mart tables (D4)."""

from datetime import date
from typing import Any

from api.repo.dashboards import fetch_mart_rows


def fetch_latest_executive_month(db_url: str) -> date:
    """Return the most recent as_of_month in fct_executive_kpis."""
    rows = fetch_mart_rows(
        "SELECT MAX(as_of_month) AS m FROM fct_executive_kpis", (), db_url
    )
    result: date = rows[0]["m"]
    return result


def fetch_executive_kpis(as_of: date, db_url: str) -> dict[str, Any]:
    rows = fetch_mart_rows(
        """
        SELECT
            k.total_loans_balance,
            k.total_deposits_balance,
            k.loan_to_deposit_ratio,
            k.core_deposit_ratio,
            k.blended_past_due_ratio,
            k.monthly_loan_growth,
            k.monthly_deposit_growth,
            k.weighted_avg_loan_rate,
            k.weighted_avg_deposit_rate,
            k.rate_spread,
            (SELECT COALESCE(SUM(monthly_loan_growth), 0)
             FROM fct_executive_kpis
             WHERE as_of_month >= DATE_TRUNC('year', %s::DATE)
               AND as_of_month <= %s) AS ytd_loan_growth,
            (SELECT COALESCE(SUM(monthly_deposit_growth), 0)
             FROM fct_executive_kpis
             WHERE as_of_month >= DATE_TRUNC('year', %s::DATE)
               AND as_of_month <= %s) AS ytd_deposit_growth
        FROM fct_executive_kpis k
        WHERE k.as_of_month = %s
        """,
        (as_of, as_of, as_of, as_of, as_of),
        db_url,
    )
    return rows[0] if rows else {}


def fetch_kpis_trend(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT as_of_month AS month,
               total_loans_balance,
               total_deposits_balance,
               blended_past_due_ratio,
               rate_spread
        FROM fct_executive_kpis
        WHERE as_of_month >= %s::DATE - INTERVAL '12 months'
          AND as_of_month <= %s
        ORDER BY as_of_month
        """,
        (as_of, as_of),
        db_url,
    )


def fetch_past_due_aging(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT bucket,
               SUM(balance)    AS balance,
               SUM(loan_count) AS loan_count
        FROM fct_delinquency_monthly
        WHERE as_of_month = %s
        GROUP BY bucket
        ORDER BY bucket
        """,
        (as_of,),
        db_url,
    )
