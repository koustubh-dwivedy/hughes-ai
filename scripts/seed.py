"""Full seed pipeline: generate → reconcile → validate → load.

Caches by content hash of profile YAML + generator source files.
Pass --force to bypass cache.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import structlog

log = structlog.get_logger()

_REPO = Path(__file__).parents[1]
_CACHE_DIR = _REPO / ".synth_cache"
_PROFILES_DIR = _REPO / "packages" / "synth-data" / "profiles"
_SRC_FILES = [
    "packages/synth-data/src/synth_data/generators/origence.py",
    "packages/synth-data/src/synth_data/generators/symitar.py",
    "packages/synth-data/src/synth_data/generators/symitar_standalone.py",
    "packages/synth-data/src/synth_data/generators/lifecycle.py",
    "packages/synth-data/src/synth_data/generators/members.py",
    "packages/synth-data/src/synth_data/generators/officers.py",
    "packages/synth-data/src/synth_data/generators/watchlist.py",
    "packages/synth-data/src/synth_data/generators/deposits.py",
    "packages/synth-data/src/synth_data/reconciliation.py",
]


def _content_hash(profile_name: str) -> str:
    h = hashlib.sha256()
    h.update((_PROFILES_DIR / f"{profile_name}.yaml").read_bytes())
    for rel in _SRC_FILES:
        h.update((_REPO / rel).read_bytes())
    return h.hexdigest()


def _cache_marker(key: str) -> Path:
    _CACHE_DIR.mkdir(exist_ok=True)
    return _CACHE_DIR / f"{key}.marker"


def _apply_grants(database_url: str) -> None:
    import psycopg as _psycopg
    stmts = [
        "GRANT USAGE ON SCHEMA public TO readonly",
        "GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public"
        " GRANT SELECT ON TABLES TO readonly",
    ]
    with _psycopg.connect(database_url) as conn:
        for stmt in stmts:
            conn.execute(stmt)
    log.info("applied readonly grants")


def _run(profile_name: str, force: bool) -> None:
    from synth_data.config import load_profile
    from synth_data.generators.deposits import generate_deposits
    from synth_data.generators.members import assign_member_id, generate_members
    from synth_data.generators.origence import generate_origence_data
    from synth_data.generators.symitar import generate_symitar_data
    from synth_data.generators.watchlist import generate_watchlist
    from synth_data.loaders.postgres import load_postgres
    from synth_data.reconciliation import reconcile
    from synth_data.validators.integrity import validate_integrity

    key = _content_hash(profile_name)
    marker = _cache_marker(key)
    if not force and marker.exists():
        log.info("cache hit — skipping seed", profile=profile_name, key=key[:12])
        return

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        log.error("DATABASE_URL env var not set")
        sys.exit(1)

    profile = load_profile(profile_name)
    log.info("loaded profile", profile=profile_name)

    origence = generate_origence_data(profile)
    log.info("generated origence data",
             applications=len(origence.applications),
             funding_events=len(origence.funding_events))

    symitar = generate_symitar_data(origence, profile)
    log.info("generated symitar data",
             booked_loans=len(symitar.booked_loans),
             loan_balances=len(symitar.loan_balances))

    branch_names = [b.branch_name for b in symitar.branches]
    members = generate_members(profile, branch_names)
    for loan in symitar.booked_loans:
        loan.member_id = assign_member_id(loan.loan_id, members)
    log.info("generated members", count=len(members))

    watchlist = generate_watchlist(
        np.random.default_rng(profile.seed + 30), symitar.booked_loans,
        watchlist_share=profile.watchlist_share,
    )
    log.info("generated watchlist", count=len(watchlist))

    deposits = generate_deposits(profile, members, branch_names)
    log.info("generated deposits",
             products=len(deposits.products), accounts=len(deposits.accounts))

    recon_rows = reconcile(origence, symitar)
    counts = {mt: sum(1 for r in recon_rows if r.match_type == mt)
              for mt in ("matched", "ambiguous", "unmatched")}
    log.info("reconciled", **counts)

    results = validate_integrity(origence, symitar, recon_rows)
    failures = [r for r in results if not r.passed]
    for f in failures:
        log.error("validation failed", check=f.check_name, detail=f.detail)
    if failures:
        sys.exit(1)
    log.info("validation passed", checks=len(results))

    load_postgres(
        origence, symitar, database_url,
        members=members, recon_rows=recon_rows,
        watchlist=watchlist, deposits=deposits,
    )
    _apply_grants(database_url)

    marker.write_text(key)
    log.info("seed complete", profile=profile_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Hughes AI database")
    parser.add_argument("--profile", required=True, help="Profile name (e.g. small_cu)")
    parser.add_argument("--force", action="store_true", help="Bypass cache")
    args = parser.parse_args()
    _run(args.profile, args.force)


if __name__ == "__main__":
    main()
