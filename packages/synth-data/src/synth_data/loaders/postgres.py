from io import StringIO

import psycopg
import structlog

from synth_data.generators.origence import OrigenceData
from synth_data.generators.symitar import BranchRow, SymitarData

log = structlog.get_logger()


_PK_COL = {
    "product_types": "product_type_id",
    "channels": "channel_id",
    "branches": "branch_id",
}


def _upsert_lookup(cur: psycopg.Cursor, table: str, names: list[str]) -> dict[str, int]:
    cur.executemany(
        f"INSERT INTO {table}(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",  # noqa: S608
        [(n,) for n in names],
    )
    pk = _PK_COL[table]
    cur.execute(f"SELECT {pk}, name FROM {table}")  # noqa: S608
    return {name: id_ for id_, name in cur.fetchall()}


def _upsert_branches(cur: psycopg.Cursor, branches: list[BranchRow]) -> dict[str, int]:
    cur.executemany(
        "INSERT INTO branches(name, region) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
        [(b.branch_name, b.region) for b in branches],
    )
    cur.execute("SELECT branch_id, name FROM branches")
    return {name: id_ for id_, name in cur.fetchall()}


def _copy_table(cur: psycopg.Cursor, sql: str, rows: list[str]) -> None:
    buf = StringIO("\n".join(rows))
    with cur.copy(sql) as copy:
        copy.write(buf.read())


def load_postgres(origence: OrigenceData, symitar: SymitarData, database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE applications CASCADE")
            log.info("truncated applications cascade")

            pt_map = _upsert_lookup(cur, "product_types", origence.product_types)
            ch_map = _upsert_lookup(cur, "channels", origence.channels)
            log.info("upserted lookup tables", product_types=len(pt_map), channels=len(ch_map))

            app_rows = [
                "\t".join([
                    r.application_id,
                    r.member_id,
                    str(pt_map[r.product_type_name]),
                    str(ch_map[r.channel_name]),
                    str(r.requested_amount),
                    r.applied_at.isoformat(),
                    r.status,
                ])
                for r in origence.applications
            ]
            _copy_table(
                cur,
                "COPY applications (application_id, member_id, product_type_id, channel_id,"
                " requested_amount, applied_at, status) FROM STDIN",
                app_rows,
            )
            log.info("loaded applications", count=len(app_rows))

            stage_rows = [
                "\t".join([
                    r.application_id,
                    r.stage_name,
                    r.entered_at.isoformat(),
                    r.exited_at.isoformat() if r.exited_at else "\\N",
                ])
                for r in origence.stages
            ]
            _copy_table(
                cur,
                "COPY stages (application_id, stage_name, entered_at, exited_at) FROM STDIN",
                stage_rows,
            )
            log.info("loaded stages", count=len(stage_rows))

            approval_rows = [
                "\t".join([
                    r.application_id,
                    r.decision,
                    r.decided_at.isoformat(),
                    str(r.approved_amount) if r.approved_amount is not None else "\\N",
                    str(r.rate) if r.rate is not None else "\\N",
                    str(r.term_months) if r.term_months is not None else "\\N",
                    r.decline_reason if r.decline_reason is not None else "\\N",
                ])
                for r in origence.approvals
            ]
            _copy_table(
                cur,
                "COPY approvals (application_id, decision, decided_at, approved_amount,"
                " rate, term_months, decline_reason) FROM STDIN",
                approval_rows,
            )
            log.info("loaded approvals", count=len(approval_rows))

            funding_rows = [
                "\t".join([
                    r.application_id,
                    r.funded_at.isoformat(),
                    str(r.funded_amount),
                ])
                for r in origence.funding_events
            ]
            _copy_table(
                cur,
                "COPY funding_events (application_id, funded_at, funded_amount) FROM STDIN",
                funding_rows,
            )
            log.info("loaded funding events", count=len(funding_rows))

            branch_map = _upsert_branches(cur, symitar.branches)
            log.info("upserted branches", count=len(branch_map))

            loan_rows = [
                "\t".join([
                    r.loan_id,
                    r.application_id if r.application_id is not None else "\\N",
                    str(branch_map[r.branch_name]),
                    r.member_id,
                    str(pt_map[r.product_type_name]),
                    r.originated_at.isoformat(),
                    str(r.original_balance),
                    str(r.balance),
                    str(r.rate),
                    str(r.term_months),
                    r.maturity_at.isoformat(),
                    r.status,
                ])
                for r in symitar.booked_loans
            ]
            _copy_table(
                cur,
                "COPY booked_loans (loan_id, application_id, branch_id, member_id,"
                " product_type_id, originated_at, original_balance, balance, rate,"
                " term_months, maturity_at, status) FROM STDIN",
                loan_rows,
            )
            log.info("loaded booked loans", count=len(loan_rows))

            bal_rows = [
                "\t".join([
                    r.balance_id,
                    r.loan_id,
                    r.snapshot_date.isoformat(),
                    str(r.balance),
                ])
                for r in symitar.loan_balances
            ]
            _copy_table(
                cur,
                "COPY loan_balances (balance_id, loan_id, snapshot_date, balance) FROM STDIN",
                bal_rows,
            )
            log.info("loaded loan balances", count=len(bal_rows))

            pmt_rows = [
                "\t".join([
                    r.payment_id,
                    r.loan_id,
                    r.paid_at.isoformat(),
                    str(r.amount),
                    str(r.principal),
                    str(r.interest),
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
            log.info("loaded payments", count=len(pmt_rows))

            delinq_rows = [
                "\t".join([
                    r.snapshot_id,
                    r.loan_id,
                    r.snapshot_date.isoformat(),
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
            log.info("loaded delinquency snapshots", count=len(delinq_rows))

        conn.commit()
        log.info("committed transaction")
