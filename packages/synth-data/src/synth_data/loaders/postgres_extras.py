"""Postgres COPY loaders for the new HUG-162 tables (dealers, households,
account_owners, card_balances, card_transactions). Kept separate from
postgres.py so that file stays under the structural cap.
"""

from io import StringIO

import psycopg
import structlog

from synth_data.generators.cards import CardData
from synth_data.generators.dealers import DealerRow
from synth_data.generators.deposits import (
    DepositAccountRow,
    DepositBalanceRow,
    DepositEventRow,
    DepositProductRow,
)
from synth_data.generators.households import HouseholdData

log = structlog.get_logger()


def _copy_table(cur: psycopg.Cursor, sql: str, rows: list[str]) -> None:
    buf = StringIO("\n".join(rows))
    with cur.copy(sql) as copy:
        copy.write(buf.read())


def load_dealers(cur: psycopg.Cursor, dealers: list[DealerRow]) -> None:
    rows = [
        "\t".join([
            d.dealer_id, d.name, d.dealer_type,
            d.address_city if d.address_city else "\\N",
            d.address_state if d.address_state else "\\N",
            d.markup_tier, d.active_from.isoformat(),
            d.active_until.isoformat() if d.active_until else "\\N",
        ])
        for d in dealers
    ]
    _copy_table(
        cur,
        "COPY dealers (dealer_id, name, dealer_type, address_city,"
        " address_state, markup_tier, active_from, active_until) FROM STDIN",
        rows,
    )
    log.info("loaded dealers", count=len(rows))


def load_households(cur: psycopg.Cursor, hh: HouseholdData) -> None:
    h_rows = [
        "\t".join([
            r.household_id, r.household_name, r.primary_member_id,
            r.formed_at.isoformat(),
            r.dissolved_at.isoformat() if r.dissolved_at else "\\N",
        ])
        for r in hh.households
    ]
    _copy_table(
        cur,
        "COPY households (household_id, household_name,"
        " primary_member_id, formed_at, dissolved_at) FROM STDIN",
        h_rows,
    )
    log.info("loaded households", count=len(h_rows))

    hm_rows = [
        "\t".join([
            r.household_member_id, r.household_id, r.member_id, r.role,
            r.joined_at.isoformat(),
            r.left_at.isoformat() if r.left_at else "\\N",
        ])
        for r in hh.household_members
    ]
    _copy_table(
        cur,
        "COPY household_members (household_member_id, household_id,"
        " member_id, role, joined_at, left_at) FROM STDIN",
        hm_rows,
    )
    log.info("loaded household members", count=len(hm_rows))

    ao_rows = [
        "\t".join([
            r.owner_id, r.owner_kind, r.owner_account_id, r.member_id, r.role,
            r.since.isoformat(),
            r.until_ts.isoformat() if r.until_ts else "\\N",
        ])
        for r in hh.account_owners
    ]
    _copy_table(
        cur,
        "COPY account_owners (owner_id, owner_kind, owner_account_id,"
        " member_id, role, since, until_ts) FROM STDIN",
        ao_rows,
    )
    log.info("loaded account owners", count=len(ao_rows))


def load_deposit_products(
    cur: psycopg.Cursor, products: list[DepositProductRow],
) -> None:
    rows = [
        "\t".join([p.product_id, p.name, "t" if p.is_core_deposit else "f"])
        for p in products
    ]
    _copy_table(
        cur,
        "COPY deposit_products (deposit_product_id, name, is_core_deposit) FROM STDIN",
        rows,
    )
    log.info("loaded deposit products", count=len(rows))


def load_deposit_accounts(
    cur: psycopg.Cursor,
    accounts: list[DepositAccountRow],
    branch_map: dict[str, int],
) -> None:
    rows = [
        "\t".join([
            a.account_id, a.member_id, str(branch_map[a.branch_name]),
            a.product_id, a.opened_at.isoformat(),
            a.closed_at.isoformat() if a.closed_at else "\\N",
            str(a.current_balance),
        ])
        for a in accounts
    ]
    _copy_table(
        cur,
        "COPY deposit_accounts (account_id, member_id, branch_id,"
        " deposit_product_id, opened_at, closed_at, current_balance) FROM STDIN",
        rows,
    )
    log.info("loaded deposit accounts", count=len(rows))


def load_deposit_balances(
    cur: psycopg.Cursor, rows: list[DepositBalanceRow],
) -> None:
    data = [
        "\t".join([r.balance_id, r.account_id, r.snapshot_date.isoformat(),
                   str(r.balance)])
        for r in rows
    ]
    _copy_table(
        cur,
        "COPY deposit_balances (balance_id, account_id, snapshot_date, balance)"
        " FROM STDIN",
        data,
    )
    log.info("loaded deposit balances", count=len(data))


def load_deposit_events(
    cur: psycopg.Cursor, rows: list[DepositEventRow],
) -> None:
    data = [
        "\t".join([r.event_id, r.account_id, r.event_type,
                   r.event_at.isoformat(), str(r.amount)])
        for r in rows
    ]
    _copy_table(
        cur,
        "COPY deposit_events (event_id, account_id, event_type, event_at, amount)"
        " FROM STDIN",
        data,
    )
    log.info("loaded deposit events", count=len(data))


def load_cards(cur: psycopg.Cursor, cards: CardData) -> None:
    bal_rows = [
        "\t".join([
            r.balance_id, r.loan_id, r.snapshot_date.isoformat(),
            str(r.balance), str(r.credit_limit),
        ])
        for r in cards.balances
    ]
    _copy_table(
        cur,
        "COPY card_balances (balance_id, loan_id, snapshot_date,"
        " balance, credit_limit) FROM STDIN",
        bal_rows,
    )
    log.info("loaded card balances", count=len(bal_rows))

    txn_rows = [
        "\t".join([
            r.transaction_id, r.loan_id, r.occurred_at.isoformat(), str(r.amount),
            r.txn_type, r.merchant_category if r.merchant_category else "\\N",
        ])
        for r in cards.transactions
    ]
    _copy_table(
        cur,
        "COPY card_transactions (transaction_id, loan_id, occurred_at,"
        " amount, txn_type, merchant_category) FROM STDIN",
        txn_rows,
    )
    log.info("loaded card transactions", count=len(txn_rows))
