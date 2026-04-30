import argparse
import os
import sys

import numpy as np
import structlog

from synth_data.config import load_profile
from synth_data.generators.deposits import generate_deposits
from synth_data.generators.members import assign_member_id, generate_members
from synth_data.generators.origence import generate_origence_data
from synth_data.generators.symitar import generate_symitar_data
from synth_data.generators.watchlist import generate_watchlist

log = structlog.get_logger()


def _cmd_generate(args: argparse.Namespace) -> None:
    profile = load_profile(args.profile)
    log.info("loaded profile", profile=args.profile, applications=profile.applications)

    origence = generate_origence_data(profile)
    log.info(
        "generated origence data",
        applications=len(origence.applications),
        stages=len(origence.stages),
        approvals=len(origence.approvals),
        funding_events=len(origence.funding_events),
    )

    symitar = generate_symitar_data(origence, profile)
    log.info(
        "generated symitar data",
        branches=len(symitar.branches),
        booked_loans=len(symitar.booked_loans),
        loan_balances=len(symitar.loan_balances),
        payments=len(symitar.payments),
        delinquency_snapshots=len(symitar.delinquency_snapshots),
    )

    branch_names = [b.branch_name for b in symitar.branches]
    members = generate_members(profile, branch_names)
    for loan in symitar.booked_loans:
        loan.member_id = assign_member_id(loan.loan_id, members)
    log.info("generated members", count=len(members))

    watchlist = generate_watchlist(
        np.random.default_rng(profile.seed + 30), symitar.booked_loans,
    )
    log.info("generated watchlist", count=len(watchlist))

    deposits = generate_deposits(profile, members, branch_names)
    log.info("generated deposits",
             products=len(deposits.products), accounts=len(deposits.accounts))

    if args.load_postgres:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            log.error("DATABASE_URL env var not set")
            sys.exit(1)
        from synth_data.loaders.postgres import load_postgres
        load_postgres(
            origence, symitar, database_url,
            members=members, watchlist=watchlist, deposits=deposits,
        )
        log.info("postgres load complete")


def main() -> None:
    parser = argparse.ArgumentParser(prog="synth_data")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate and optionally load synthetic data")
    gen.add_argument("--profile", required=True, help="Profile name (e.g. small_cu)")
    gen.add_argument(
        "--load-postgres", action="store_true", help="Load into DATABASE_URL",
    )

    args = parser.parse_args()
    if args.command == "generate":
        _cmd_generate(args)


if __name__ == "__main__":
    main()
