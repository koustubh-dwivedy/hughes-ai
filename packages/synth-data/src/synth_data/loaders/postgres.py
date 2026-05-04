from io import StringIO

import psycopg
import structlog

from synth_data.generators.cards import CardData
from synth_data.generators.dealers import DealerRow
from synth_data.generators.deposits import DepositData
from synth_data.generators.households import HouseholdData
from synth_data.generators.members import MemberRow
from synth_data.generators.origence import OrigenceData
from synth_data.generators.symitar_types import BranchRow, OfficerRow, SymitarData
from synth_data.generators.watchlist import WatchlistRow
from synth_data.loaders.postgres_extras import (
    load_cards as _load_cards,
)
from synth_data.loaders.postgres_extras import (
    load_dealers as _load_dealers,
)
from synth_data.loaders.postgres_extras import (
    load_deposit_accounts as _load_deposit_accounts,
)
from synth_data.loaders.postgres_extras import (
    load_deposit_balances as _load_deposit_balances,
)
from synth_data.loaders.postgres_extras import (
    load_deposit_events as _load_deposit_events,
)
from synth_data.loaders.postgres_extras import (
    load_deposit_products as _load_deposit_products,
)
from synth_data.loaders.postgres_extras import (
    load_households as _load_households,
)
from synth_data.loaders.postgres_loans import (
    load_booked_loans as _load_booked_loans,
)
from synth_data.loaders.postgres_loans import (
    load_loan_details as _load_loan_details,
)
from synth_data.loaders.postgres_loans import (
    load_loan_lifecycle_events as _load_loan_lifecycle_events,
)
from synth_data.loaders.postgres_loans import (
    load_reconciliation_bridge as _load_reconciliation_bridge,
)
from synth_data.loaders.postgres_loans import (
    load_watchlist as _load_watchlist,
)
from synth_data.reconciliation import ReconciliationRow

log = structlog.get_logger()

_INSERT_SQL = {
    "product_types": (
        "INSERT INTO product_types(name) VALUES (%s) ON CONFLICT (name) DO NOTHING"
    ),
    "channels": "INSERT INTO channels(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
}
_SELECT_SQL = {
    "product_types": "SELECT product_type_id, name FROM product_types",
    "channels": "SELECT channel_id, name FROM channels",
}


def _upsert_lookup(cur: psycopg.Cursor, table: str, names: list[str]) -> dict[str, int]:
    cur.executemany(_INSERT_SQL[table], [(n,) for n in names])
    cur.execute(_SELECT_SQL[table])
    return {name: id_ for id_, name in cur.fetchall()}


def _upsert_branches(cur: psycopg.Cursor, branches: list[BranchRow]) -> dict[str, int]:
    cur.executemany(
        "INSERT INTO branches(name, region) VALUES (%s, %s)"
        " ON CONFLICT (name) DO NOTHING",
        [(b.branch_name, b.region) for b in branches],
    )
    cur.execute("SELECT branch_id, name FROM branches")
    return {name: id_ for id_, name in cur.fetchall()}


def _copy_table(cur: psycopg.Cursor, sql: str, rows: list[str]) -> None:
    buf = StringIO("\n".join(rows))
    with cur.copy(sql) as copy:
        copy.write(buf.read())


def _load_applications(
    cur: psycopg.Cursor,
    origence: OrigenceData,
    pt_map: dict[str, int],
    ch_map: dict[str, int],
) -> None:
    rows = [
        "\t".join([
            r.application_id, r.member_id,
            str(pt_map[r.product_type_name]), str(ch_map[r.channel_name]),
            str(r.requested_amount), r.applied_at.isoformat(), r.status,
        ])
        for r in origence.applications
    ]
    _copy_table(
        cur,
        "COPY applications (application_id, member_id, product_type_id,"
        " channel_id, requested_amount, applied_at, status) FROM STDIN",
        rows,
    )
    log.info("loaded applications", count=len(rows))


def _load_stages_approvals_funding(cur: psycopg.Cursor, origence: OrigenceData) -> None:
    stage_rows = [
        "\t".join([
            r.application_id, r.stage_name, r.entered_at.isoformat(),
            r.exited_at.isoformat() if r.exited_at else "\\N",
        ])
        for r in origence.stages
    ]
    _copy_table(
        cur,
        "COPY stages (application_id, stage_name, entered_at, exited_at)"
        " FROM STDIN",
        stage_rows,
    )
    appr_rows = [
        "\t".join([
            r.application_id, r.decision, r.decided_at.isoformat(),
            str(r.approved_amount) if r.approved_amount is not None else "\\N",
            str(r.rate) if r.rate is not None else "\\N",
            str(r.term_months) if r.term_months is not None else "\\N",
            r.decline_reason if r.decline_reason is not None else "\\N",
        ])
        for r in origence.approvals
    ]
    _copy_table(
        cur,
        "COPY approvals (application_id, decision, decided_at,"
        " approved_amount, rate, term_months, decline_reason) FROM STDIN",
        appr_rows,
    )
    fund_rows = [
        "\t".join([r.application_id, r.funded_at.isoformat(), str(r.funded_amount)])
        for r in origence.funding_events
    ]
    _copy_table(
        cur,
        "COPY funding_events (application_id, funded_at, funded_amount) FROM STDIN",
        fund_rows,
    )
    log.info(
        "loaded origence detail",
        stages=len(stage_rows), approvals=len(appr_rows), fundings=len(fund_rows),
    )


def _load_members(
    cur: psycopg.Cursor, members: list[MemberRow], branch_map: dict[str, int],
) -> None:
    rows = [
        "\t".join([
            m.member_id, m.first_name, m.last_name,
            m.joined_at.isoformat(), str(branch_map[m.home_branch_name]),
        ])
        for m in members
    ]
    _copy_table(
        cur,
        "COPY members (member_id, first_name, last_name, joined_at, home_branch_id)"
        " FROM STDIN",
        rows,
    )
    log.info("loaded members", count=len(rows))


def _load_officers(
    cur: psycopg.Cursor, officers: list[OfficerRow], branch_map: dict[str, int],
) -> None:
    rows = [
        "\t".join([
            o.officer_id, o.name, str(branch_map[o.branch_name]),
            o.hired_at.isoformat(), o.status,
        ])
        for o in officers
    ]
    _copy_table(
        cur,
        "COPY officers (officer_id, name, branch_id, hired_at, status) FROM STDIN",
        rows,
    )
    log.info("loaded officers", count=len(rows))


def _load_origence_side(
    cur: psycopg.Cursor,
    origence: OrigenceData,
    members: list[MemberRow] | None,
    dealers: list[DealerRow] | None,
    branch_map: dict[str, int],
) -> dict[str, int]:
    pt_map = _upsert_lookup(cur, "product_types", origence.product_types)
    ch_map = _upsert_lookup(cur, "channels", origence.channels)
    _load_applications(cur, origence, pt_map, ch_map)
    _load_stages_approvals_funding(cur, origence)
    if members is not None:
        cur.execute("TRUNCATE members CASCADE")
        _load_members(cur, members, branch_map)
    if dealers is not None:
        _load_dealers(cur, dealers)
    return pt_map


def _load_symitar_side(
    cur: psycopg.Cursor,
    symitar: SymitarData,
    pt_map: dict[str, int],
    branch_map: dict[str, int],
    recon_rows: list[ReconciliationRow] | None,
    watchlist: list[WatchlistRow] | None,
) -> None:
    _load_officers(cur, symitar.officers, branch_map)
    _load_booked_loans(cur, symitar, pt_map, branch_map)
    _load_loan_details(cur, symitar)
    cur.execute("TRUNCATE loan_lifecycle_events")
    _load_loan_lifecycle_events(cur, symitar.loan_lifecycle_events)
    if recon_rows is not None:
        _load_reconciliation_bridge(cur, recon_rows)
    if watchlist is not None:
        cur.execute("TRUNCATE watchlist")
        _load_watchlist(cur, watchlist)


def _load_deposits_side(
    cur: psycopg.Cursor,
    deposits: DepositData,
    branch_map: dict[str, int],
) -> None:
    cur.execute(
        "TRUNCATE deposit_accounts, deposit_products,"
        " deposit_balances, deposit_events CASCADE"
    )
    _load_deposit_products(cur, deposits.products)
    _load_deposit_accounts(cur, deposits.accounts, branch_map)
    _load_deposit_balances(cur, deposits.balances)
    _load_deposit_events(cur, deposits.events)


def load_postgres(
    origence: OrigenceData,
    symitar: SymitarData,
    database_url: str,
    members: list[MemberRow] | None = None,
    recon_rows: list[ReconciliationRow] | None = None,
    watchlist: list[WatchlistRow] | None = None,
    deposits: DepositData | None = None,
    dealers: list[DealerRow] | None = None,
    households: HouseholdData | None = None,
    cards: CardData | None = None,
) -> None:
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE applications CASCADE")
        cur.execute("TRUNCATE officers CASCADE")
        cur.execute(
            "TRUNCATE card_transactions, card_balances, account_owners,"
            " household_members, households, dealers CASCADE"
        )
        branch_map = _upsert_branches(cur, symitar.branches)
        pt_map = _load_origence_side(cur, origence, members, dealers, branch_map)
        _load_symitar_side(cur, symitar, pt_map, branch_map, recon_rows, watchlist)
        if deposits is not None:
            _load_deposits_side(cur, deposits, branch_map)
        if households is not None:
            _load_households(cur, households)
        if cards is not None:
            _load_cards(cur, cards)
        conn.commit()
        log.info("committed transaction")
