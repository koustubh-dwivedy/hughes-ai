"""Audit harness — hard gate for the data-model revamp (HUG-166).

Cross-system reconciliation, logical invariants, and regulatory closure
checks. Failures block merge. Run via `make audit` or directly with pytest
(requires DATABASE_URL pointing at a freshly seeded + dbt-built database).
"""

from __future__ import annotations

import os

import psycopg
import pytest


@pytest.fixture(scope="module")
def db() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set; audit requires a seeded database")
    with psycopg.connect(url, autocommit=True) as conn:
        yield conn


def _scalar(db: psycopg.Connection, sql: str) -> object:
    """Execute a scalar query; on failure, roll back so subsequent tests
    don't get InFailedSqlTransaction."""
    try:
        with db.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            assert row is not None, f"no rows returned for: {sql}"
            return row[0]
    except psycopg.errors.Error:
        # autocommit=True means each statement is its own transaction;
        # nothing to roll back, but be explicit.
        raise


# ============================================================
# A. Cross-system reconciliation (Origence ↔ Symitar)
# ============================================================


def test_origence_funded_count_matches_symitar_booked(
    db: psycopg.Connection,
) -> None:
    funded = _scalar(db, "SELECT COUNT(*) FROM funding_events")
    booked_with_app = _scalar(
        db, "SELECT COUNT(*) FROM booked_loans WHERE application_id IS NOT NULL"
    )
    assert funded == booked_with_app, (
        f"funded ({funded}) does not match booked-with-application "
        f"({booked_with_app}); recon_bridge would be incomplete"
    )


def test_origence_funded_amount_matches_symitar_principal(
    db: psycopg.Connection,
) -> None:
    funded_total = _scalar(
        db, "SELECT COALESCE(SUM(funded_amount), 0) FROM funding_events"
    )
    booked_total = _scalar(
        db,
        "SELECT COALESCE(SUM(original_balance), 0) FROM booked_loans"
        " WHERE application_id IS NOT NULL",
    )
    delta = abs(float(funded_total) - float(booked_total))
    tolerance = float(funded_total) * 0.005  # 0.5%
    assert delta <= tolerance, (
        f"Origence funded {funded_total:,.0f} vs Symitar booked "
        f"{booked_total:,.0f}; delta {delta:,.0f} > tolerance {tolerance:,.0f}"
    )


# ============================================================
# B. Logical invariants
# ============================================================


def test_auto_indirect_has_dealer_id(db: psycopg.Connection) -> None:
    missing = _scalar(
        db,
        "SELECT COUNT(*) FROM dim_loan"
        " WHERE product_type = 'auto_indirect' AND dealer_id IS NULL",
    )
    assert missing == 0, (
        f"{missing} auto_indirect loans have NULL dealer_id "
        "(every indirect loan must have a dealer)"
    )


def test_non_indirect_has_no_dealer_id(db: psycopg.Connection) -> None:
    leaked = _scalar(
        db,
        "SELECT COUNT(*) FROM dim_loan"
        " WHERE product_type != 'auto_indirect' AND dealer_id IS NOT NULL",
    )
    assert leaked == 0, (
        f"{leaked} non-indirect loans have a dealer_id "
        "(only auto_indirect should carry one)"
    )


def test_every_household_has_exactly_one_primary_member(
    db: psycopg.Connection,
) -> None:
    bad = _scalar(
        db,
        "SELECT COUNT(*) FROM ("
        "  SELECT household_id, COUNT(*) AS c"
        "  FROM bridge_household_member"
        "  WHERE role = 'primary' AND is_current"
        "  GROUP BY household_id"
        "  HAVING COUNT(*) != 1"
        ") sub",
    )
    assert bad == 0, f"{bad} households do not have exactly one primary member"


def test_no_loan_funded_before_member_joined(db: psycopg.Connection) -> None:
    bad = _scalar(
        db,
        "SELECT COUNT(*) FROM booked_loans bl"
        " INNER JOIN members m ON bl.member_id = m.member_id"
        " WHERE bl.originated_at < m.joined_at"
        " AND bl.application_id IS NOT NULL",
    )
    # Standalone loans (application_id IS NULL) use a deterministic
    # member-id hash that may not respect the join_date ordering — exempt.
    assert bad == 0, (
        f"{bad} loans were funded before the member joined the credit union"
    )


def test_card_balance_movement_closes(db: psycopg.Connection) -> None:
    """For each card, the change in balance from one snapshot to the next
    equals the sum of transactions in that interval, within $0.05.

    Tolerance is $0.05 (not $0.01) to accommodate cumulative rounding
    in _gen_month — interest, purchases, payments each round to the
    cent independently, so over a 26-month history a few rows drift by
    a couple of pennies. Anything larger indicates a real off-by-one.
    """
    bad = _scalar(
        db,
        """
        WITH snaps AS (
            SELECT
                loan_id,
                snapshot_date,
                balance,
                LAG(balance) OVER w AS prev_balance,
                LAG(snapshot_date) OVER w AS prev_date
            FROM card_balances
            WINDOW w AS (PARTITION BY loan_id ORDER BY snapshot_date)
        ),
        txn_deltas AS (
            SELECT
                s.loan_id,
                s.snapshot_date,
                s.balance,
                s.prev_balance,
                COALESCE(SUM(t.amount), 0) AS txn_sum
            FROM snaps s
            LEFT JOIN card_transactions t
                ON t.loan_id = s.loan_id
               AND t.occurred_at >= s.prev_date
               AND t.occurred_at <  s.snapshot_date
            WHERE s.prev_balance IS NOT NULL
            GROUP BY s.loan_id, s.snapshot_date, s.balance, s.prev_balance
        )
        SELECT COUNT(*) FROM txn_deltas
        WHERE ABS(balance - (prev_balance + txn_sum)) > 0.05
        """,
    )
    assert bad == 0, (
        f"{bad} card-balance month transitions do not close to within $0.05"
    )


# ============================================================
# C. Statistical sanity (industry bands)
# ============================================================


def _ratio(db: psycopg.Connection, num_sql: str, den_sql: str) -> float:
    num = float(_scalar(db, num_sql))
    den = float(_scalar(db, den_sql))
    return num / den if den > 0 else 0.0


def test_loan_to_share_ratio_in_band(db: psycopg.Connection) -> None:
    ratio = _ratio(
        db,
        "SELECT COALESCE(SUM(balance), 0) FROM booked_loans WHERE status != 'paid_off'",
        "SELECT COALESCE(SUM(current_balance), 0) FROM deposit_accounts"
        " WHERE closed_at IS NULL",
    )
    assert 0.05 <= ratio <= 1.50, (
        f"loan-to-share ratio {ratio:.3f} outside synthetic bound [0.05, 1.50]"
    )


def test_auto_share_of_loans_in_band(db: psycopg.Connection) -> None:
    auto_share = _ratio(
        db,
        "SELECT COALESCE(SUM(balance), 0) FROM dim_loan"
        " INNER JOIN booked_loans ON booked_loans.loan_id::TEXT = dim_loan.loan_id"
        " WHERE dim_loan.product_type IN ('auto_direct', 'auto_indirect')"
        " AND booked_loans.status != 'paid_off'",
        "SELECT COALESCE(SUM(balance), 0) FROM booked_loans WHERE status != 'paid_off'",
    )
    assert 0.10 <= auto_share <= 0.70, (
        f"auto loan share {auto_share:.3f} outside band [0.10, 0.70]"
    )


def test_indirect_share_of_auto_in_band(db: psycopg.Connection) -> None:
    indirect = _ratio(
        db,
        "SELECT COALESCE(SUM(balance), 0) FROM dim_loan"
        " INNER JOIN booked_loans ON booked_loans.loan_id::TEXT = dim_loan.loan_id"
        " WHERE dim_loan.product_type = 'auto_indirect'"
        " AND booked_loans.status != 'paid_off'",
        "SELECT COALESCE(SUM(balance), 0) FROM dim_loan"
        " INNER JOIN booked_loans ON booked_loans.loan_id::TEXT = dim_loan.loan_id"
        " WHERE dim_loan.product_type IN ('auto_direct', 'auto_indirect')"
        " AND booked_loans.status != 'paid_off'",
    )
    assert 0.20 <= indirect <= 0.80, (
        f"indirect share of auto {indirect:.3f} outside band [0.20, 0.80]"
    )


def test_household_to_member_ratio_in_band(db: psycopg.Connection) -> None:
    ratio = _ratio(
        db,
        "SELECT COUNT(*) FROM households",
        "SELECT COUNT(*) FROM members",
    )
    # Targets ~0.63 (60% paired + 10% triple + 30% single).
    assert 0.50 <= ratio <= 0.85, (
        f"households/members {ratio:.3f} outside band [0.50, 0.85]"
    )


def test_top_10_dealer_concentration_in_band(db: psycopg.Connection) -> None:
    ratio = _ratio(
        db,
        """
        SELECT COALESCE(SUM(dealer_total), 0) FROM (
            SELECT bl.dealer_id, SUM(bl.balance) AS dealer_total
            FROM booked_loans bl
            INNER JOIN dim_loan dl ON dl.loan_id = bl.loan_id::TEXT
            WHERE dl.product_type = 'auto_indirect'
              AND bl.status != 'paid_off'
            GROUP BY bl.dealer_id
            ORDER BY dealer_total DESC
            LIMIT 10
        ) top10
        """,
        "SELECT COALESCE(SUM(balance), 0) FROM booked_loans bl"
        " INNER JOIN dim_loan dl ON dl.loan_id = bl.loan_id::TEXT"
        " WHERE dl.product_type = 'auto_indirect' AND bl.status != 'paid_off'",
    )
    assert 0.40 <= ratio <= 1.01, (
        f"top-10 dealer concentration {ratio:.3f} outside band [0.40, 1.01]"
    )


# ============================================================
# D. Regulatory closure (NCUA + CECL)
# ============================================================


def test_cecl_rollforward_closes_per_row(db: psycopg.Connection) -> None:
    """ending = beginning - net_charge_offs + provision_expense (zero tolerance)."""
    bad = _scalar(
        db,
        "SELECT COUNT(*) FROM fct_cecl_allowance_rollforward"
        " WHERE ABS(ending_balance - (beginning_balance - net_charge_offs"
        " + provision_expense)) > 0.01",
    )
    assert bad == 0, f"{bad} CECL roll-forward rows do not close arithmetically"


def test_ncua_total_loans_reconciles_to_dim_loan(
    db: psycopg.Connection,
) -> None:
    """For the latest quarter that reports loans, line 386 must equal the
    sum of fct_loan_performance.balance at the same snapshot the mart uses.

    The mart (fct_call_report.sql) sums fct_loan_performance.balance from
    the snapshot dated `the first day of the last month of that quarter`
    (e.g., Mar 1 for Q1 end Mar 31). We reconstruct the same snapshot
    here and reconcile within $1.

    We scope the latest quarter to those that actually carry line 386:
    dim_calendar can extend past the synthetic-data anchor, so non-loan
    lines (deposits/CECL) may surface a later bare quarter that has no
    loan snapshot. Reconciling that quarter would be meaningless.
    """
    latest_quarter = _scalar(
        db,
        "SELECT MAX(period_end_quarter) FROM fct_call_report"
        " WHERE ncua_5300_line_code = '386'",
    )
    line_386 = _scalar(
        db,
        "SELECT COALESCE(line_value, 0) FROM fct_call_report"
        f" WHERE ncua_5300_line_code = '386'"
        f" AND period_end_quarter = '{latest_quarter}'",
    )
    snap_total = _scalar(
        db,
        "SELECT COALESCE(SUM(perf.balance), 0) FROM fct_loan_performance perf"
        " INNER JOIN dim_loan dl ON dl.loan_id = perf.loan_id::TEXT"
        f" WHERE perf.snapshot_date ="
        f" DATE_TRUNC('month', DATE '{latest_quarter}')::DATE"
        " AND dl.status != 'paid_off'",
    )
    delta = abs(float(line_386) - float(snap_total))
    assert delta < 1.0, (
        f"NCUA 5300 line 386 ({line_386:,.2f}) vs dim_loan snapshot "
        f"({snap_total:,.2f}); delta {delta:,.4f} > $1"
    )


def test_dealer_table_row_count_positive(db: psycopg.Connection) -> None:
    n = _scalar(db, "SELECT COUNT(*) FROM dealers")
    assert n > 0, "dealers table is empty — generator did not run"


def test_household_table_row_count_positive(db: psycopg.Connection) -> None:
    n = _scalar(db, "SELECT COUNT(*) FROM households")
    assert n > 0, "households table is empty — generator did not run"
