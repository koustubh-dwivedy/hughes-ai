"""Dashboard service: date helpers, TTL cache, and panel composers."""

import time
from datetime import date

from api.repo import dashboards as repo
from api.types.deposit_portfolio import (
    AccountActivity,
    BranchBalance,
    DepositPortfolioData,
    NewVsClosed,
    ProductBalance,
    ProductDelta,
    TopDeposit,
)

_TTL = 300.0
_cache: dict[tuple[str, str], tuple[float, object]] = {}


def _monotonic() -> float:
    return time.monotonic()


# ── Date helpers ──────────────────────────────────────────────────────────────


def mtd_range(as_of: date) -> tuple[date, date]:
    """Return (first of month, as_of)."""
    return date(as_of.year, as_of.month, 1), as_of


def ytd_range(as_of: date) -> tuple[date, date]:
    """Return (Jan 1 of current year, as_of)."""
    return date(as_of.year, 1, 1), as_of


def prior_ytd_range(as_of: date) -> tuple[date, date]:
    """Return same day-of-year window one year earlier."""
    return date(as_of.year - 1, 1, 1), date(as_of.year - 1, as_of.month, as_of.day)


# ── In-process TTL cache ──────────────────────────────────────────────────────


def cache_get(endpoint: str, as_of_date: str) -> object | None:
    """Return cached value for (endpoint, as_of_date) or None if absent/expired."""
    entry = _cache.get((endpoint, as_of_date))
    if entry is None:
        return None
    expires_at, value = entry
    if _monotonic() > expires_at:
        del _cache[(endpoint, as_of_date)]
        return None
    return value


def cache_set(endpoint: str, as_of_date: str, value: object) -> None:
    """Store value in cache with a _TTL-second expiry."""
    _cache[(endpoint, as_of_date)] = (_monotonic() + _TTL, value)


def cache_clear() -> None:
    """Evict all entries — used in tests."""
    _cache.clear()


# ── Panel composers ───────────────────────────────────────────────────────────


def compose_deposit_portfolio(as_of: date, db_url: str) -> DepositPortfolioData:
    """Fetch and assemble all panels for the deposit-portfolio dashboard."""
    totals = repo.fetch_deposit_totals(as_of, db_url)
    top25 = repo.fetch_top_depositors(25, db_url)
    branches = repo.fetch_deposits_by_branch(as_of, db_url)
    mix = repo.fetch_deposit_mix(as_of, db_url)
    delta = repo.fetch_change_by_product(as_of, db_url)
    nvc = repo.fetch_new_vs_closed(as_of, db_url)

    total_bal = float(totals.get("total_deposits") or 0)

    return DepositPortfolioData(
        total_deposits=total_bal,
        mtd_change=float(totals.get("mtd_change") or 0),
        ytd_change=float(totals.get("ytd_change") or 0),
        avg_balance_per_customer=float(totals.get("avg_balance") or 0),
        account_count=int(totals.get("account_count") or 0),
        top_25_deposits=[
            TopDeposit(
                member_name=str(r["member_name"]),
                balance=float(r["balance"]),
                share_pct=float(r["balance"]) / total_bal * 100 if total_bal else 0.0,
            )
            for r in top25
        ],
        deposits_by_branch=[
            BranchBalance(
                branch_name=str(r["branch_name"]), balance=float(r["balance"])
            )
            for r in branches
        ],
        deposit_mix=[
            ProductBalance(
                product=str(r["product"]),
                balance=float(r["balance"]),
                share_pct=float(r["balance"]) / total_bal * 100 if total_bal else 0.0,
            )
            for r in mix
        ],
        change_by_product=[
            ProductDelta(product=str(r["product"]), delta=float(r["delta"]))
            for r in delta
        ],
        new_vs_closed_accounts=NewVsClosed(
            opened=AccountActivity(
                count=int(nvc.get("opened_count") or 0),
                amount=float(nvc.get("opened_amount") or 0),
            ),
            closed=AccountActivity(
                count=int(nvc.get("closed_count") or 0),
                amount=float(nvc.get("closed_amount") or 0),
            ),
        ),
    )
