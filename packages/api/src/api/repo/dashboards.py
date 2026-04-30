"""Read-only access helpers for dashboard mart tables."""

from datetime import date
from typing import Any

import psycopg


def fetch_mart_rows(
    sql: str,
    params: tuple[object, ...],
    db_url: str,
) -> list[dict[str, Any]]:
    """Execute a parameterised read-only query and return rows as dicts."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description or []]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


# ── Deposit portfolio ─────────────────────────────────────────────────────────


def fetch_latest_deposit_month(db_url: str) -> date:
    """Return the most recent as_of_month present in fct_deposits_monthly."""
    rows = fetch_mart_rows(
        "SELECT MAX(as_of_month) AS m FROM fct_deposits_monthly", (), db_url
    )
    result: date = rows[0]["m"]
    return result


def fetch_deposit_totals(as_of: date, db_url: str) -> dict[str, Any]:
    rows = fetch_mart_rows(
        """
        SELECT
            SUM(total_balance)                          AS total_deposits,
            SUM(mtd_change)                             AS mtd_change,
            SUM(ytd_change)                             AS ytd_change,
            SUM(account_count)                          AS account_count,
            SUM(total_balance) / NULLIF(SUM(account_count), 0) AS avg_balance
        FROM fct_deposits_monthly
        WHERE as_of_month = %s
        """,
        (as_of,),
        db_url,
    )
    return rows[0] if rows else {}


def fetch_top_depositors(limit: int, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT m.first_name || ' ' || m.last_name AS member_name,
               SUM(da.current_balance)             AS balance
        FROM deposit_accounts da
        JOIN members m ON da.member_id = m.member_id
        WHERE da.closed_at IS NULL
        GROUP BY m.member_id, m.first_name, m.last_name
        ORDER BY balance DESC
        LIMIT %s
        """,
        (limit,),
        db_url,
    )


def fetch_deposits_by_branch(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT b.name AS branch_name, SUM(f.total_balance) AS balance
        FROM fct_deposits_monthly f
        JOIN branches b ON f.branch_id = b.branch_id
        WHERE f.as_of_month = %s
        GROUP BY b.name
        ORDER BY balance DESC
        """,
        (as_of,),
        db_url,
    )


def fetch_deposit_mix(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT dp.product_name AS product, SUM(f.total_balance) AS balance
        FROM fct_deposits_monthly f
        JOIN dim_deposit_product dp USING (deposit_product_id)
        WHERE f.as_of_month = %s
        GROUP BY dp.product_name
        ORDER BY balance DESC
        """,
        (as_of,),
        db_url,
    )


def fetch_change_by_product(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT dp.product_name AS product, SUM(f.ytd_change) AS delta
        FROM fct_deposits_monthly f
        JOIN dim_deposit_product dp USING (deposit_product_id)
        WHERE f.as_of_month = %s
        GROUP BY dp.product_name
        ORDER BY delta DESC
        """,
        (as_of,),
        db_url,
    )


def fetch_new_vs_closed(as_of: date, db_url: str) -> dict[str, Any]:
    rows = fetch_mart_rows(
        """
        SELECT
            SUM(opened_count)                            AS opened_count,
            SUM(closed_count)                            AS closed_count,
            SUM(opened_count * avg_balance_per_customer) AS opened_amount,
            SUM(closed_count * avg_balance_per_customer) AS closed_amount
        FROM fct_deposits_monthly
        WHERE as_of_month = %s
        """,
        (as_of,),
        db_url,
    )
    return rows[0] if rows else {}


# ── Past-due / delinquency ────────────────────────────────────────────────────


def fetch_latest_delinquency_month(db_url: str) -> date:
    """Return the most recent as_of_month in fct_delinquency_monthly."""
    rows = fetch_mart_rows(
        "SELECT MAX(as_of_month) AS m FROM fct_delinquency_monthly", (), db_url
    )
    result: date = rows[0]["m"]
    return result


def fetch_delinquency_kpis(as_of: date, db_url: str) -> dict[str, Any]:
    rows = fetch_mart_rows(
        """
        SELECT
            SUM(CASE WHEN bucket IN ('30-59','60-89','90+')
                     THEN balance ELSE 0 END) AS past_due_total,
            SUM(CASE WHEN bucket = '90+'
                     THEN balance ELSE 0 END) AS nonperforming_balance
        FROM fct_delinquency_monthly
        WHERE as_of_month = %s
        """,
        (as_of,),
        db_url,
    )
    return rows[0] if rows else {}


def fetch_nonaccrual_total(last_day: date, db_url: str) -> float:
    rows = fetch_mart_rows(
        """
        SELECT COALESCE(SUM(lb.balance), 0) AS nonaccrual_total
        FROM booked_loans bl
        JOIN loan_balances lb ON bl.loan_id = lb.loan_id
        WHERE bl.is_nonaccrual = TRUE
          AND lb.snapshot_date = (
              SELECT MAX(snapshot_date) FROM loan_balances
              WHERE snapshot_date <= %s
          )
        """,
        (last_day,),
        db_url,
    )
    return float(rows[0]["nonaccrual_total"]) if rows else 0.0


def fetch_watchlist_count(last_day: date, db_url: str) -> int:
    rows = fetch_mart_rows(
        """
        SELECT COUNT(*) AS cnt
        FROM watchlist
        WHERE added_at::DATE <= %s
          AND (removed_at IS NULL OR removed_at::DATE > %s)
        """,
        (last_day, last_day),
        db_url,
    )
    return int(rows[0]["cnt"]) if rows else 0


def fetch_past_due_by_officer(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT o.officer_name,
               SUM(f.balance)             AS balance,
               SUM(f.past_due_loan_count) AS count
        FROM fct_delinquency_monthly f
        JOIN dim_officer o USING (officer_id)
        WHERE f.as_of_month = %s
          AND f.bucket IN ('30-59', '60-89', '90+')
        GROUP BY o.officer_id, o.officer_name
        ORDER BY balance DESC
        """,
        (as_of,),
        db_url,
    )


def fetch_delinquency_trend(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT
            as_of_month AS month,
            SUM(CASE WHEN bucket = '30-59' THEN balance ELSE 0 END) AS bucket_30_59,
            SUM(CASE WHEN bucket = '60-89' THEN balance ELSE 0 END) AS bucket_60_89,
            SUM(CASE WHEN bucket = '90+'   THEN balance ELSE 0 END) AS bucket_90_plus
        FROM fct_delinquency_monthly
        WHERE as_of_month >= %s::DATE - INTERVAL '12 months'
          AND as_of_month <= %s
        GROUP BY as_of_month
        ORDER BY as_of_month
        """,
        (as_of, as_of),
        db_url,
    )


def fetch_lifecycle_tab(tab: str, as_of: date, db_url: str) -> list[dict[str, Any]]:
    if tab not in {"new", "renewed", "paid_off"}:
        return []
    return fetch_mart_rows(
        """
        SELECT
            as_of_month                AS period,
            product_type,
            SUM(loan_count)::int       AS count,
            SUM(total_amount)          AS amount
        FROM fct_loan_lifecycle_events
        WHERE event_type = %s
          AND as_of_month <= %s
          AND as_of_month >= (%s::DATE - INTERVAL '12 months')::DATE
        GROUP BY as_of_month, product_type
        ORDER BY as_of_month DESC, product_type
        """,
        (tab, as_of, as_of),
        db_url,
    )


def fetch_watchlist_trend(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        SELECT
            TO_CHAR(months.month, 'YYYY-MM')    AS month,
            COUNT(w.watchlist_id)::int          AS count,
            COALESCE(SUM(bl.balance), 0)        AS balance
        FROM generate_series(
                (%s::DATE - INTERVAL '12 months')::DATE,
                %s::DATE,
                '1 month'::INTERVAL
             ) AS months(month)
        LEFT JOIN watchlist w
               ON w.added_at::DATE < (months.month + INTERVAL '1 month')::DATE
              AND (w.removed_at IS NULL OR w.removed_at::DATE > months.month::DATE)
        LEFT JOIN booked_loans bl ON bl.loan_id = w.loan_id
        GROUP BY months.month
        ORDER BY months.month
        """,
        (as_of, as_of),
        db_url,
    )


def fetch_past_due_ratio_trend(as_of: date, db_url: str) -> list[dict[str, Any]]:
    return fetch_mart_rows(
        """
        WITH past_due AS (
            SELECT as_of_month, SUM(balance) AS past_due_bal
            FROM fct_delinquency_monthly
            WHERE bucket IN ('30-59', '60-89', '90+')
              AND as_of_month >= %s::DATE - INTERVAL '12 months'
              AND as_of_month <= %s
            GROUP BY as_of_month
        ),
        total AS (
            SELECT as_of_month, SUM(total_balance) AS total_bal
            FROM fct_loans_monthly
            WHERE as_of_month >= %s::DATE - INTERVAL '12 months'
              AND as_of_month <= %s
            GROUP BY as_of_month
        )
        SELECT p.as_of_month AS month,
               p.past_due_bal / NULLIF(t.total_bal, 0) AS ratio
        FROM past_due p
        JOIN total t USING (as_of_month)
        ORDER BY month
        """,
        (as_of, as_of, as_of, as_of),
        db_url,
    )
