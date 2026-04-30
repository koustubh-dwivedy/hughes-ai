"""Dashboard service: date helpers, TTL cache, and panel composers."""

import calendar
import time
from datetime import date, timedelta
from typing import Any

from api.repo import dashboards as repo
from api.repo import loans as repo_loans
from api.types.deposit_portfolio import (
    AccountActivity,
    BranchBalance,
    DepositPortfolioData,
    NewVsClosed,
    ProductBalance,
    ProductDelta,
    TopDeposit,
)
from api.types.officer_branch import (
    ComboBalanceRate,
    LifecycleTabRow,
    LoanMixItem,
    OfficerBranchData,
    SingleLoanCount,
    TopBorrower,
    WatchlistTrendPoint,
    WaterfallStep,
)
from api.types.past_due import (
    DelinquencyTrendMonth,
    OfficerDelinquency,
    PastDueData,
    PastDueRatioPoint,
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


def _build_nvc(nvc: dict[str, Any]) -> NewVsClosed:
    return NewVsClosed(
        opened=AccountActivity(
            count=int(nvc.get("opened_count") or 0),
            amount=float(nvc.get("opened_amount") or 0),
        ),
        closed=AccountActivity(
            count=int(nvc.get("closed_count") or 0),
            amount=float(nvc.get("closed_amount") or 0),
        ),
    )


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
        new_vs_closed_accounts=_build_nvc(nvc),
    )


def _prior_month(as_of: date) -> date:
    return (date(as_of.year, as_of.month, 1) - timedelta(days=1)).replace(day=1)


def _month_last_day(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def compose_past_due(as_of: date, db_url: str) -> PastDueData:
    """Fetch and assemble all panels for the past-due dashboard."""
    prior = _prior_month(as_of)
    last = _month_last_day(as_of)
    prior_last = _month_last_day(prior)

    kpis = repo.fetch_delinquency_kpis(as_of, db_url)
    kpis_p = repo.fetch_delinquency_kpis(prior, db_url)
    nac = repo.fetch_nonaccrual_total(last, db_url)
    wl = repo.fetch_watchlist_count(last, db_url)
    wl_p = repo.fetch_watchlist_count(prior_last, db_url)
    by_officer = repo.fetch_past_due_by_officer(as_of, db_url)
    trend = repo.fetch_delinquency_trend(as_of, db_url)
    ratio_trend = repo.fetch_past_due_ratio_trend(as_of, db_url)
    pdt = float(kpis.get("past_due_total") or 0)
    pdt_p = float(kpis_p.get("past_due_total") or 0)
    npb = float(kpis.get("nonperforming_balance") or 0)
    npb_p = float(kpis_p.get("nonperforming_balance") or 0)
    return PastDueData(
        past_due_total=pdt,
        past_due_total_delta=pdt - pdt_p,
        nonaccrual_total=nac,
        nonaccrual_total_delta=0.0,
        watchlist_count=wl,
        watchlist_count_delta=wl - wl_p,
        nonperforming_balance=npb,
        nonperforming_balance_delta=npb - npb_p,
        past_due_by_officer=[
            OfficerDelinquency(
                officer_name=str(r["officer_name"]),
                balance=float(r["balance"]),
                count=int(r["count"]),
            )
            for r in by_officer
        ],
        delinquency_trend_13_months=[
            DelinquencyTrendMonth(
                month=r["month"],
                bucket_30_59=float(r["bucket_30_59"]),
                bucket_60_89=float(r["bucket_60_89"]),
                bucket_90_plus=float(r["bucket_90_plus"]),
            )
            for r in trend
        ],
        past_due_ratio_trend=[
            PastDueRatioPoint(month=r["month"], ratio=float(r["ratio"]))
            for r in ratio_trend
        ],
    )


# ── Officer / branch composer ─────────────────────────────────────────────────


def _build_combo_rate(rows: list[dict[str, Any]]) -> list[ComboBalanceRate]:
    return [
        ComboBalanceRate(
            product=str(r["product"]),
            balance=float(r["balance"]),
            weighted_avg_rate=float(r["weighted_avg_rate"]),
        )
        for r in rows
    ]


def compose_officer_branch(
    as_of: date,
    db_url: str,
    branch_id: int | None = None,
    officer_id: str | None = None,
    tab: str | None = None,
) -> OfficerBranchData:
    """Fetch and assemble all panels for the officer-branch dashboard."""
    prior = _prior_month(as_of)
    totals = repo_loans.fetch_loan_totals(as_of, db_url, branch_id, officer_id)
    top25 = repo_loans.fetch_top_borrowers(25, db_url, branch_id, officer_id)
    mix = repo_loans.fetch_loan_mix(as_of, db_url, branch_id, officer_id)
    wfall = repo_loans.fetch_change_by_loan_type(
        as_of, prior, db_url, branch_id, officer_id
    )
    slc = repo_loans.fetch_single_loan_counts(as_of, db_url, branch_id, officer_id)
    combo = repo_loans.fetch_combo_balance_rate(as_of, db_url, branch_id, officer_id)
    wl_trend = repo.fetch_watchlist_trend(as_of, db_url)
    tab_rows = repo.fetch_lifecycle_tab(tab, as_of, db_url) if tab is not None else None
    tb = float(totals.get("total_loans") or 0)
    return OfficerBranchData(
        total_loans=tb,
        account_count=int(totals.get("account_count") or 0),
        avg_loan_balance=float(totals.get("avg_loan_balance") or 0),
        top_25_borrowers=[
            TopBorrower(
                member_name=str(r["member_name"]),
                balance=float(r["balance"]),
                share_pct=float(r["balance"]) / tb * 100 if tb else 0.0,
            )
            for r in top25
        ],
        loan_mix_donut=[
            LoanMixItem(
                product=str(r["product"]),
                balance=float(r["balance"]),
                share_pct=float(r["balance"]) / tb * 100 if tb else 0.0,
            )
            for r in mix
        ],
        change_by_type_waterfall=[
            WaterfallStep(product=str(r["product"]), delta=float(r["delta"]))
            for r in wfall
        ],
        single_loan_customers_by_type=[
            SingleLoanCount(product=str(r["product"]), count=int(r["count"]))
            for r in slc
        ],
        combo_balance_rate=_build_combo_rate(combo),
        watchlist_trend=[
            WatchlistTrendPoint(
                month=str(r["month"]),
                count=int(r["count"]),
                balance=float(r["balance"]),
            )
            for r in wl_trend
        ],
        tab_data=[
            LifecycleTabRow(
                period=str(r["period"]),
                product_type=str(r["product_type"]),
                count=int(r["count"]),
                amount=float(r["amount"]),
            )
            for r in tab_rows
        ]
        if tab_rows is not None
        else None,
    )
