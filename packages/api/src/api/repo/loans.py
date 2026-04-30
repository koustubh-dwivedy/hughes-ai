"""Read-only access helpers for loan mart tables (D3a)."""

from datetime import date
from typing import Any

from api.repo.dashboards import fetch_mart_rows


def fetch_latest_loans_month(db_url: str) -> date:
    """Return the most recent as_of_month in fct_loans_monthly."""
    rows = fetch_mart_rows(
        "SELECT MAX(as_of_month) AS m FROM fct_loans_monthly", (), db_url
    )
    result: date = rows[0]["m"]
    return result


def fetch_loan_totals(
    as_of: date,
    db_url: str,
    branch_id: int | None,
    officer_id: str | None,
) -> dict[str, Any]:
    rows = fetch_mart_rows(
        """
        SELECT
            SUM(total_balance)                              AS total_loans,
            SUM(loan_count)                                 AS account_count,
            SUM(total_balance) / NULLIF(SUM(loan_count), 0) AS avg_loan_balance
        FROM fct_loans_monthly f
        WHERE f.as_of_month = %s
          AND (%s::INT IS NULL OR f.branch_id = %s::INT)
          AND (%s::TEXT IS NULL OR f.officer_id = %s::TEXT)
        """,
        (as_of, branch_id, branch_id, officer_id, officer_id),
        db_url,
    )
    return rows[0] if rows else {}


def fetch_top_borrowers(
    limit: int,
    db_url: str,
    branch_id: int | None,
    officer_id: str | None,
) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT m.first_name || ' ' || m.last_name AS member_name,
               SUM(lb.balance)                     AS balance
        FROM booked_loans bl
        JOIN loan_balances lb ON bl.loan_id = lb.loan_id
        JOIN members m ON bl.member_id = m.member_id
        WHERE lb.snapshot_date = (SELECT MAX(snapshot_date) FROM loan_balances)
          AND (%s::INT IS NULL OR bl.branch_id = %s::INT)
          AND (%s::TEXT IS NULL OR bl.officer_id::TEXT = %s::TEXT)
        GROUP BY m.member_id, m.first_name, m.last_name
        ORDER BY balance DESC
        LIMIT %s
        """,
        (branch_id, branch_id, officer_id, officer_id, limit),
        db_url,
    )


def fetch_loan_mix(
    as_of: date,
    db_url: str,
    branch_id: int | None,
    officer_id: str | None,
) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT f.product_type AS product, SUM(f.total_balance) AS balance
        FROM fct_loans_monthly f
        WHERE f.as_of_month = %s
          AND (%s::INT IS NULL OR f.branch_id = %s::INT)
          AND (%s::TEXT IS NULL OR f.officer_id = %s::TEXT)
        GROUP BY f.product_type
        ORDER BY balance DESC
        """,
        (as_of, branch_id, branch_id, officer_id, officer_id),
        db_url,
    )


def fetch_change_by_loan_type(
    as_of: date,
    prior: date,
    db_url: str,
    branch_id: int | None,
    officer_id: str | None,
) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT product_type AS product,
               SUM(CASE WHEN as_of_month = %s THEN total_balance ELSE 0 END) -
               SUM(CASE WHEN as_of_month = %s THEN total_balance ELSE 0 END) AS delta
        FROM fct_loans_monthly f
        WHERE f.as_of_month IN (%s, %s)
          AND (%s::INT IS NULL OR f.branch_id = %s::INT)
          AND (%s::TEXT IS NULL OR f.officer_id = %s::TEXT)
        GROUP BY product_type
        ORDER BY delta DESC
        """,
        (as_of, prior, as_of, prior, branch_id, branch_id, officer_id, officer_id),
        db_url,
    )


def fetch_single_loan_counts(
    as_of: date,
    db_url: str,
    branch_id: int | None,
    officer_id: str | None,
) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT f.product_type AS product,
               SUM(f.single_loan_customer_count) AS count
        FROM fct_loans_monthly f
        WHERE f.as_of_month = %s
          AND (%s::INT IS NULL OR f.branch_id = %s::INT)
          AND (%s::TEXT IS NULL OR f.officer_id = %s::TEXT)
        GROUP BY f.product_type
        ORDER BY count DESC
        """,
        (as_of, branch_id, branch_id, officer_id, officer_id),
        db_url,
    )


def fetch_combo_balance_rate(
    as_of: date,
    db_url: str,
    branch_id: int | None,
    officer_id: str | None,
) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT f.product_type AS product,
               SUM(f.total_balance) AS balance,
               SUM(f.total_balance * f.weighted_avg_rate)
                   / NULLIF(SUM(f.total_balance), 0) AS weighted_avg_rate
        FROM fct_loans_monthly f
        WHERE f.as_of_month = %s
          AND (%s::INT IS NULL OR f.branch_id = %s::INT)
          AND (%s::TEXT IS NULL OR f.officer_id = %s::TEXT)
        GROUP BY f.product_type
        ORDER BY balance DESC
        """,
        (as_of, branch_id, branch_id, officer_id, officer_id),
        db_url,
    )
