"""Origence Connect LOS synthetic generator.

Replaces the legacy hard-coded 8-product taxonomy with the new 6-product
catalog loaded from packages/synth-data/profiles/products.yaml. Member IDs
on applications now reference real members from the members table — no
more disjoint UUID generation.
"""

import bisect
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from synth_data.config import LoanProductSpec, ProductCatalog, SynthProfile
from synth_data.generators.members import MemberRow
from synth_data.generators.origence_types import (
    ApplicationRow,
    ApprovalRow,
    FundingEventRow,
    OrigenceData,
    StageRow,
    _Arrays,
)

__all__ = [
    "ApplicationRow", "StageRow", "ApprovalRow", "FundingEventRow",
    "OrigenceData", "CHANNELS", "DECLINE_REASONS", "generate_origence_data",
]

CHANNELS = ["branch", "online", "mobile", "indirect", "call_center"]
DECLINE_REASONS = ["credit_score", "dti_ratio", "incomplete_docs", "policy"]

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)


def _gen_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _channel_for_product(rng: np.random.Generator, product: LoanProductSpec) -> str:
    """Auto-Indirect always books through 'indirect' (dealer); others draw freely."""
    if product.code == "auto_indirect":
        return "indirect"
    # Non-indirect products avoid the 'indirect' channel.
    non_indirect = [c for c in CHANNELS if c != "indirect"]
    return non_indirect[int(rng.integers(0, len(non_indirect)))]


def _sample_by_product(
    rng: np.random.Generator,
    pt_idxs: Any,
    products: list[LoanProductSpec],
) -> tuple[list[int], list[float], list[int]]:
    amounts: list[int] = []
    rates: list[float] = []
    terms: list[int] = []
    for idx in pt_idxs:
        spec = products[int(idx)]
        lo, hi = spec.amount_range
        # Round to nearest $500 for non-card; cards round to $100 (credit limits)
        step = 100 if spec.code == "credit_card" else 500
        amounts.append(int(rng.integers(lo // step, hi // step + 1)) * step)
        r_lo, r_hi = spec.rate_range
        rates.append(float(rng.uniform(r_lo, r_hi)) if r_lo < r_hi else r_lo)
        terms.append(int(rng.choice(spec.term_months)))
    return amounts, rates, terms


def _assign_statuses(
    status_r: Any,
    approval_rate: float,
    funding_rate: float,
) -> list[str]:
    withdrawn_thresh = 0.03
    declined_thresh = withdrawn_thresh + (1.0 - approval_rate)
    approved_thresh = declined_thresh + approval_rate * (1.0 - funding_rate)
    conditions = [
        status_r < withdrawn_thresh,
        status_r < declined_thresh,
        status_r < approved_thresh,
    ]
    choices = ["withdrawn", "declined", "approved"]
    return list(np.select(conditions, choices, default="funded"))


def _pre_generate(
    rng: np.random.Generator,
    n: int,
    products: list[LoanProductSpec],
    member_count: int,
    max_days_ago: int = 730,
) -> _Arrays:
    mix = np.array([p.mix for p in products])
    pt_idxs = rng.choice(len(products), n, p=mix)
    amounts, appr_rates, term_idxs = _sample_by_product(rng, pt_idxs, products)
    return _Arrays(
        app_uuids=_gen_uuids(rng, n),
        member_picks=rng.integers(0, member_count, n),
        pt_idxs=pt_idxs,
        ch_idxs=rng.integers(0, len(CHANNELS), n),
        amounts=amounts,
        days_ago=rng.integers(0, max_days_ago, n),
        status_r=rng.random(n),
        stage_hrs=rng.integers(1, 24, (n, 4)),
        stage_days=rng.integers(1, 8, (n, 4)),
        appr_days=rng.integers(3, 15, n),
        appr_factors=rng.uniform(0.8, 1.0, n),
        appr_rates=appr_rates,
        term_idxs=term_idxs,
        decline_idxs=rng.integers(0, len(DECLINE_REASONS), n),
        fund_days=rng.integers(1, 15, n),
    )


def _append_decision(
    i: int,
    app_id: str,
    decided_at: datetime,
    dec_exit: datetime,
    status: str,
    arr: _Arrays,
    approvals: list[ApprovalRow],
    stages: list[StageRow],
    funding_events: list[FundingEventRow],
) -> None:
    if status == "declined":
        approvals.append(ApprovalRow(
            application_id=app_id,
            decision="declined",
            decided_at=decided_at,
            approved_amount=None,
            rate=None,
            term_months=None,
            decline_reason=DECLINE_REASONS[int(arr.decline_idxs[i])],
        ))
        return
    raw_amount = arr.amounts[i] * float(arr.appr_factors[i])
    approved_amount = Decimal(str(round(raw_amount, 2)))
    approvals.append(ApprovalRow(
        application_id=app_id,
        decision="approved",
        decided_at=decided_at,
        approved_amount=approved_amount,
        rate=Decimal(str(round(float(arr.appr_rates[i]), 4))),
        term_months=int(arr.term_idxs[i]),
        decline_reason=None,
    ))
    if status == "funded":
        close_exit = dec_exit + timedelta(days=int(arr.stage_days[i, 1]))
        stages.append(StageRow(app_id, "closing", dec_exit, close_exit))
        funded_at = decided_at + timedelta(days=int(arr.fund_days[i]))
        funding_events.append(FundingEventRow(
            application_id=app_id,
            funded_at=funded_at,
            funded_amount=approved_amount,
        ))


def _pick_eligible_member(
    members_sorted: list[MemberRow],
    joined_at_keys: list[datetime],
    applied_at: datetime,
    raw_pick: int,
) -> MemberRow:
    """Pick a member who joined on or before applied_at (HUG-168). Members
    are pre-sorted by joined_at; we bisect_right to find how many qualify
    and pick within that prefix using the deterministic raw_pick % count.
    Falls back to the earliest-joining member if no one qualifies (would
    only happen if applied_at predates every member, which the synth
    profile prevents)."""
    eligible_count = bisect.bisect_right(joined_at_keys, applied_at)
    if eligible_count == 0:
        return members_sorted[0]
    return members_sorted[raw_pick % eligible_count]


def _build_one_app(
    i: int,
    rng: np.random.Generator,
    arr: _Arrays,
    members: list[MemberRow],
    products: list[LoanProductSpec],
    status: str,
    applications: list[ApplicationRow],
    stages: list[StageRow],
    approvals: list[ApprovalRow],
    funding_events: list[FundingEventRow],
    members_sorted: list[MemberRow],
    joined_at_keys: list[datetime],
) -> None:
    app_id = arr.app_uuids[i]
    applied_at = _REF_DATE - timedelta(days=int(arr.days_ago[i]))
    product = products[int(arr.pt_idxs[i])]
    chosen_member = _pick_eligible_member(
        members_sorted, joined_at_keys, applied_at, int(arr.member_picks[i]),
    )
    applications.append(ApplicationRow(
        application_id=app_id,
        member_id=chosen_member.member_id,
        product_type_name=product.code,
        channel_name=_channel_for_product(rng, product),
        requested_amount=Decimal(str(arr.amounts[i])),
        applied_at=applied_at,
        status=status,
    ))
    sub_exit = applied_at + timedelta(hours=int(arr.stage_hrs[i, 0]))
    stages.append(StageRow(app_id, "submitted", applied_at, sub_exit))
    if status == "withdrawn":
        return
    uw_exit = sub_exit + timedelta(days=int(arr.stage_days[i, 0]))
    stages.append(StageRow(app_id, "underwriting", sub_exit, uw_exit))
    dec_exit = uw_exit + timedelta(hours=int(arr.stage_hrs[i, 1]))
    stages.append(StageRow(app_id, "decision", uw_exit, dec_exit))
    decided_at = applied_at + timedelta(days=int(arr.appr_days[i]))
    _append_decision(
        i, app_id, decided_at, dec_exit, status, arr,
        approvals, stages, funding_events,
    )


def generate_origence_data(
    profile: SynthProfile,
    catalog: ProductCatalog,
    members: list[MemberRow],
) -> OrigenceData:
    rng = np.random.default_rng(profile.seed)
    n = profile.applications
    products = catalog.loan_products
    arr = _pre_generate(
        rng, n, products, member_count=len(members),
        max_days_ago=profile.history_months * 31,
    )
    statuses = _assign_statuses(
        arr.status_r, profile.approval_rate, profile.funding_rate,
    )
    applications: list[ApplicationRow] = []
    stages: list[StageRow] = []
    approvals: list[ApprovalRow] = []
    funding_events: list[FundingEventRow] = []
    members_sorted = sorted(members, key=lambda m: m.joined_at)
    joined_at_keys = [m.joined_at for m in members_sorted]
    for i in range(n):
        _build_one_app(
            i, rng, arr, members, products, statuses[i],
            applications, stages, approvals, funding_events,
            members_sorted, joined_at_keys,
        )
    return OrigenceData(
        product_types=[p.code for p in products],
        channels=CHANNELS,
        applications=applications,
        stages=stages,
        approvals=approvals,
        funding_events=funding_events,
    )
