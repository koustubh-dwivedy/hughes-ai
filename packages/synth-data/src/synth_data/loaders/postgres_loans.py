"""Loan-side COPY loaders, extracted from postgres.py to keep that file
under the structural cap."""

from io import StringIO

import psycopg
import structlog

from synth_data.generators.symitar_types import (
    LoanLifecycleEventRow,
    SymitarData,
)
from synth_data.generators.watchlist import WatchlistRow
from synth_data.reconciliation import ReconciliationRow

log = structlog.get_logger()


def _copy_table(cur: psycopg.Cursor, sql: str, rows: list[str]) -> None:
    buf = StringIO("\n".join(rows))
    with cur.copy(sql) as copy:
        copy.write(buf.read())


def load_booked_loans(
    cur: psycopg.Cursor,
    symitar: SymitarData,
    pt_map: dict[str, int],
    branch_map: dict[str, int],
) -> None:
    rows = [
        "\t".join([
            r.loan_id, r.application_id if r.application_id is not None else "\\N",
            str(branch_map[r.branch_name]), r.member_id,
            str(pt_map[r.product_type_name]),
            r.originated_at.isoformat(), str(r.original_balance),
            str(r.balance), str(r.rate), str(r.term_months),
            r.maturity_at.isoformat(), r.status,
            r.officer_id if r.officer_id is not None else "\\N",
            "t" if r.is_nonaccrual else "f",
            r.dealer_id if r.dealer_id is not None else "\\N",
            (str(r.dealer_reserve_amount)
             if r.dealer_reserve_amount is not None else "\\N"),
        ])
        for r in symitar.booked_loans
    ]
    _copy_table(
        cur,
        "COPY booked_loans (loan_id, application_id, branch_id, member_id,"
        " product_type_id, originated_at, original_balance, balance, rate,"
        " term_months, maturity_at, status, officer_id, is_nonaccrual,"
        " dealer_id, dealer_reserve_amount) FROM STDIN",
        rows,
    )
    log.info("loaded booked loans", count=len(rows))


def load_loan_details(cur: psycopg.Cursor, symitar: SymitarData) -> None:
    bal_rows = [
        "\t".join([r.balance_id, r.loan_id, r.snapshot_date.isoformat(),
                   str(r.balance)])
        for r in symitar.loan_balances
    ]
    _copy_table(
        cur,
        "COPY loan_balances (balance_id, loan_id, snapshot_date, balance) FROM STDIN",
        bal_rows,
    )
    pmt_rows = [
        "\t".join([
            r.payment_id, r.loan_id, r.paid_at.isoformat(),
            str(r.amount), str(r.principal), str(r.interest),
            r.payment_method if r.payment_method is not None else "\\N",
        ])
        for r in symitar.payments
    ]
    _copy_table(
        cur,
        "COPY payments (payment_id, loan_id, paid_at, amount, principal,"
        " interest, payment_method) FROM STDIN",
        pmt_rows,
    )
    delinq_rows = [
        "\t".join([
            r.snapshot_id, r.loan_id, r.snapshot_date.isoformat(),
            str(r.days_past_due),
            r.delinquency_bucket if r.delinquency_bucket is not None else "\\N",
        ])
        for r in symitar.delinquency_snapshots
    ]
    _copy_table(
        cur,
        "COPY delinquency_snapshots (snapshot_id, loan_id, snapshot_date,"
        " days_past_due, delinquency_bucket) FROM STDIN",
        delinq_rows,
    )


def load_loan_lifecycle_events(
    cur: psycopg.Cursor, rows: list[LoanLifecycleEventRow],
) -> None:
    data = [
        "\t".join([r.event_id, r.loan_id, r.event_month.isoformat(), r.event_type])
        for r in rows
    ]
    _copy_table(
        cur,
        "COPY loan_lifecycle_events (event_id, loan_id, event_month, event_type)"
        " FROM STDIN",
        data,
    )


def load_watchlist(cur: psycopg.Cursor, rows: list[WatchlistRow]) -> None:
    wl_rows = [
        "\t".join([
            r.watchlist_id, r.loan_id, r.added_at.isoformat(),
            r.removed_at.isoformat() if r.removed_at else "\\N",
            r.reason,
        ])
        for r in rows
    ]
    _copy_table(
        cur,
        "COPY watchlist (watchlist_id, loan_id, added_at, removed_at, reason)"
        " FROM STDIN",
        wl_rows,
    )


def load_reconciliation_bridge(
    cur: psycopg.Cursor, rows: list[ReconciliationRow],
) -> None:
    cur.executemany(
        "INSERT INTO reconciliation_bridge(application_id, loan_id, match_type)"
        " VALUES (%s, %s, %s)",
        [(r.application_id, r.loan_id, r.match_type) for r in rows],
    )
