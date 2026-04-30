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
