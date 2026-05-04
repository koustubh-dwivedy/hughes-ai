import argparse
import os
import sys
from dataclasses import dataclass

import numpy as np
import structlog

from synth_data.config import (
    ProductCatalog,
    SynthProfile,
    load_product_catalog,
    load_profile,
)
from synth_data.generators.cards import CardData, generate_card_data
from synth_data.generators.dealers import DealerRow, generate_dealers
from synth_data.generators.deposits import DepositData, generate_deposits
from synth_data.generators.households import HouseholdData, generate_households
from synth_data.generators.members import MemberRow, assign_member_id, generate_members
from synth_data.generators.origence import OrigenceData, generate_origence_data
from synth_data.generators.symitar import (
    BRANCH_NAMES,
    REGIONS,
    SymitarData,
    generate_symitar_data,
)
from synth_data.generators.symitar_types import BranchRow
from synth_data.generators.watchlist import WatchlistRow, generate_watchlist

log = structlog.get_logger()


@dataclass
class _Pipeline:
    profile: SynthProfile
    catalog: ProductCatalog
    branches: list[BranchRow]
    members: list[MemberRow]
    dealers: list[DealerRow]
    origence: OrigenceData
    symitar: SymitarData
    deposits: DepositData
    households: HouseholdData
    cards: CardData
    watchlist: list[WatchlistRow]


def _build_branches(profile: SynthProfile) -> list[BranchRow]:
    return [
        BranchRow(branch_name=BRANCH_NAMES[i], region=REGIONS[i % len(REGIONS)])
        for i in range(profile.branch_count)
    ]


def _restamp_standalone_member_ids(
    symitar: SymitarData, members: list[MemberRow],
) -> None:
    """Standalone branch loans inherit deterministic member IDs from the hash of
    loan_id + branch (preserves legacy dim_member rollups). Application-linked
    loans already carry the real member_id from origence."""
    for loan in symitar.booked_loans:
        if loan.application_id is None:
            loan.member_id = assign_member_id(loan.loan_id, members)


def _build_pipeline(profile: SynthProfile, catalog: ProductCatalog) -> _Pipeline:
    branches = _build_branches(profile)
    branch_names = [b.branch_name for b in branches]
    members = generate_members(profile, branch_names)
    log.info("generated members", count=len(members))
    dealers = generate_dealers(profile)
    log.info("generated dealers", count=len(dealers))
    origence = generate_origence_data(profile, catalog, members)
    log.info("generated origence", funded=len(origence.funding_events))
    symitar = generate_symitar_data(origence, profile, catalog, dealers=dealers)
    log.info("generated symitar", booked_loans=len(symitar.booked_loans))
    _restamp_standalone_member_ids(symitar, members)
    watchlist = generate_watchlist(
        np.random.default_rng(profile.seed + 30), symitar.booked_loans,
    )
    log.info("generated watchlist", count=len(watchlist))
    deposits = generate_deposits(profile, members, branch_names)
    log.info("generated deposits", accounts=len(deposits.accounts))
    households = generate_households(
        profile, members, deposits.accounts, symitar.booked_loans,
    )
    log.info("generated households", households=len(households.households))
    cards = generate_card_data(profile, symitar.booked_loans)
    log.info("generated cards", balances=len(cards.balances))
    return _Pipeline(
        profile=profile, catalog=catalog, branches=branches, members=members,
        dealers=dealers, origence=origence, symitar=symitar, deposits=deposits,
        households=households, cards=cards, watchlist=watchlist,
    )


def _load_to_postgres(pipeline: _Pipeline) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        log.error("DATABASE_URL env var not set")
        sys.exit(1)
    from synth_data.loaders.postgres import load_postgres
    load_postgres(
        pipeline.origence, pipeline.symitar, database_url,
        members=pipeline.members, watchlist=pipeline.watchlist,
        deposits=pipeline.deposits, dealers=pipeline.dealers,
        households=pipeline.households, cards=pipeline.cards,
    )
    log.info("postgres load complete")


def _cmd_generate(args: argparse.Namespace) -> None:
    profile = load_profile(args.profile)
    catalog = load_product_catalog()
    log.info("loaded profile + catalog", profile=args.profile)
    pipeline = _build_pipeline(profile, catalog)
    if args.load_postgres:
        _load_to_postgres(pipeline)


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
