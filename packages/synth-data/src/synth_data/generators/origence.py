import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from synth_data.config import SynthProfile

PRODUCT_TYPES = [
    "cre", "c_and_i", "residential", "auto",
    "construction", "home_equity", "consumer", "ppp",
]
_PRODUCT_MIX = [0.06, 0.07, 0.26, 0.28, 0.04, 0.10, 0.15, 0.04]

PRODUCT_SPECS: dict[str, dict[str, Any]] = {
    "cre": {
        "rate": (0.060, 0.090),
        "terms": [60, 84, 120, 180, 240, 300],
        "amount": (500_000, 5_000_000),
    },
    "c_and_i": {
        "rate": (0.050, 0.080),
        "terms": [36, 48, 60, 84, 120],
        "amount": (100_000, 2_000_000),
    },
    "residential": {
        "rate": (0.030, 0.070),
        "terms": [180, 240, 360],
        "amount": (100_000, 700_000),
    },
    "auto": {
        "rate": (0.040, 0.100),
        "terms": [36, 48, 60, 72, 84],
        "amount": (15_000, 60_000),
    },
    "construction": {
        "rate": (0.060, 0.090),
        "terms": [12, 18, 24],
        "amount": (200_000, 3_000_000),
    },
    "home_equity": {
        "rate": (0.040, 0.080),
        "terms": [60, 84, 120, 180],
        "amount": (20_000, 150_000),
    },
    "consumer": {
        "rate": (0.080, 0.180),
        "terms": [12, 24, 36, 48, 60],
        "amount": (1_000, 25_000),
    },
    "ppp": {
        "rate": (0.010, 0.010),
        "terms": [24, 60],
        "amount": (5_000, 150_000),
    },
}

CHANNELS = ["branch", "online", "mobile", "indirect", "call_center"]
DECLINE_REASONS = ["credit_score", "dti_ratio", "incomplete_docs", "policy"]

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)


@dataclass
class ApplicationRow:
    application_id: str
    member_id: str
    product_type_name: str
    channel_name: str
    requested_amount: Decimal
    applied_at: datetime
    status: str


@dataclass
class StageRow:
    application_id: str
    stage_name: str
    entered_at: datetime
    exited_at: datetime | None


@dataclass
class ApprovalRow:
    application_id: str
    decision: str
    decided_at: datetime
    approved_amount: Decimal | None
    rate: Decimal | None
    term_months: int | None
    decline_reason: str | None


@dataclass
class FundingEventRow:
    application_id: str
    funded_at: datetime
    funded_amount: Decimal


@dataclass
class OrigenceData:
    product_types: list[str]
    channels: list[str]
    applications: list[ApplicationRow]
    stages: list[StageRow]
    approvals: list[ApprovalRow]
    funding_events: list[FundingEventRow]


@dataclass
class _Arrays:
    app_uuids: list[str]
    member_uuids: list[str]
    pt_idxs: Any
    ch_idxs: Any
    amounts: list[int]
    days_ago: Any
    status_r: Any
    stage_hrs: Any
    stage_days: Any
    appr_days: Any
    appr_factors: Any
    appr_rates: list[float]
    term_idxs: list[int]
    decline_idxs: Any
    fund_days: Any


def _gen_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _sample_by_product(
    rng: np.random.Generator, pt_idxs: Any
) -> tuple[list[int], list[float], list[int]]:
    amounts: list[int] = []
    rates: list[float] = []
    terms: list[int] = []
    for idx in pt_idxs:
        spec = PRODUCT_SPECS[PRODUCT_TYPES[int(idx)]]
        lo, hi = spec["amount"]
        amounts.append(int(rng.integers(lo // 500, hi // 500 + 1)) * 500)
        r_lo, r_hi = spec["rate"]
        rates.append(float(rng.uniform(r_lo, r_hi)) if r_lo < r_hi else r_lo)
        terms.append(int(rng.choice(spec["terms"])))
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


def _pre_generate(rng: np.random.Generator, n: int, max_days_ago: int = 730) -> _Arrays:
    pt_idxs = rng.choice(len(PRODUCT_TYPES), n, p=_PRODUCT_MIX)
    amounts, appr_rates, term_idxs = _sample_by_product(rng, pt_idxs)
    return _Arrays(
        app_uuids=_gen_uuids(rng, n),
        member_uuids=_gen_uuids(rng, n),
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


def generate_origence_data(profile: SynthProfile) -> OrigenceData:
    rng = np.random.default_rng(profile.seed)
    n = profile.applications
    arr = _pre_generate(rng, n, max_days_ago=profile.history_months * 31)
    statuses = _assign_statuses(
        arr.status_r, profile.approval_rate, profile.funding_rate,
    )

    applications: list[ApplicationRow] = []
    stages: list[StageRow] = []
    approvals: list[ApprovalRow] = []
    funding_events: list[FundingEventRow] = []

    for i in range(n):
        app_id = arr.app_uuids[i]
        applied_at = _REF_DATE - timedelta(days=int(arr.days_ago[i]))
        status = statuses[i]
        applications.append(ApplicationRow(
            application_id=app_id,
            member_id=arr.member_uuids[i],
            product_type_name=PRODUCT_TYPES[int(arr.pt_idxs[i])],
            channel_name=CHANNELS[int(arr.ch_idxs[i])],
            requested_amount=Decimal(str(arr.amounts[i])),
            applied_at=applied_at,
            status=status,
        ))
        sub_exit = applied_at + timedelta(hours=int(arr.stage_hrs[i, 0]))
        stages.append(StageRow(app_id, "submitted", applied_at, sub_exit))
        if status == "withdrawn":
            continue
        uw_exit = sub_exit + timedelta(days=int(arr.stage_days[i, 0]))
        stages.append(StageRow(app_id, "underwriting", sub_exit, uw_exit))
        dec_exit = uw_exit + timedelta(hours=int(arr.stage_hrs[i, 1]))
        stages.append(StageRow(app_id, "decision", uw_exit, dec_exit))
        decided_at = applied_at + timedelta(days=int(arr.appr_days[i]))
        _append_decision(
            i, app_id, decided_at, dec_exit, status, arr,
            approvals, stages, funding_events,
        )

    return OrigenceData(
        product_types=PRODUCT_TYPES,
        channels=CHANNELS,
        applications=applications,
        stages=stages,
        approvals=approvals,
        funding_events=funding_events,
    )
