from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
import uuid

import numpy as np

from synth_data.config import SynthProfile

PRODUCT_TYPES = ["auto", "personal_loan", "mortgage", "home_equity", "credit_card", "rv"]
CHANNELS = ["branch", "online", "mobile", "indirect", "call_center"]
DECLINE_REASONS = ["credit_score", "dti_ratio", "incomplete_docs", "policy"]
TERM_MONTHS = [12, 24, 36, 48, 60, 72, 84]

_REF_DATE = datetime(2026, 4, 1, tzinfo=timezone.utc)


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
    exited_at: Optional[datetime]


@dataclass
class ApprovalRow:
    application_id: str
    decision: str
    decided_at: datetime
    approved_amount: Optional[Decimal]
    rate: Optional[Decimal]
    term_months: Optional[int]
    decline_reason: Optional[str]


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


def _gen_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _assign_statuses(
    status_r: np.ndarray,
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


def generate_origence_data(profile: SynthProfile) -> OrigenceData:
    rng = np.random.default_rng(profile.seed)
    n = profile.applications

    app_uuids = _gen_uuids(rng, n)
    member_uuids = _gen_uuids(rng, n)
    pt_idxs = rng.integers(0, len(PRODUCT_TYPES), n)
    ch_idxs = rng.integers(0, len(CHANNELS), n)
    amounts = (rng.integers(10, 151, n) * 500).tolist()
    days_ago = rng.integers(0, 730, n)
    status_r = rng.random(n)
    stage_hrs = rng.integers(1, 24, (n, 4))
    stage_days = rng.integers(1, 8, (n, 4))
    appr_days = rng.integers(3, 15, n)
    appr_factors = rng.uniform(0.8, 1.0, n)
    appr_rates = rng.uniform(0.04, 0.18, n)
    term_idxs = rng.integers(0, len(TERM_MONTHS), n)
    decline_idxs = rng.integers(0, len(DECLINE_REASONS), n)
    fund_days = rng.integers(1, 15, n)

    statuses = _assign_statuses(status_r, profile.approval_rate, profile.funding_rate)

    applications: list[ApplicationRow] = []
    stages: list[StageRow] = []
    approvals: list[ApprovalRow] = []
    funding_events: list[FundingEventRow] = []

    for i in range(n):
        app_id = app_uuids[i]
        applied_at = _REF_DATE - timedelta(days=int(days_ago[i]))
        status = statuses[i]

        applications.append(ApplicationRow(
            application_id=app_id,
            member_id=member_uuids[i],
            product_type_name=PRODUCT_TYPES[int(pt_idxs[i])],
            channel_name=CHANNELS[int(ch_idxs[i])],
            requested_amount=Decimal(str(amounts[i])),
            applied_at=applied_at,
            status=status,
        ))

        sub_exit = applied_at + timedelta(hours=int(stage_hrs[i, 0]))
        stages.append(StageRow(app_id, "submitted", applied_at, sub_exit))

        if status == "withdrawn":
            continue

        uw_exit = sub_exit + timedelta(days=int(stage_days[i, 0]))
        stages.append(StageRow(app_id, "underwriting", sub_exit, uw_exit))
        dec_exit = uw_exit + timedelta(hours=int(stage_hrs[i, 1]))
        stages.append(StageRow(app_id, "decision", uw_exit, dec_exit))

        decided_at = applied_at + timedelta(days=int(appr_days[i]))

        if status == "declined":
            approvals.append(ApprovalRow(
                application_id=app_id,
                decision="declined",
                decided_at=decided_at,
                approved_amount=None,
                rate=None,
                term_months=None,
                decline_reason=DECLINE_REASONS[int(decline_idxs[i])],
            ))
            continue

        approved_amount = Decimal(str(round(amounts[i] * float(appr_factors[i]), 2)))
        approvals.append(ApprovalRow(
            application_id=app_id,
            decision="approved",
            decided_at=decided_at,
            approved_amount=approved_amount,
            rate=Decimal(str(round(float(appr_rates[i]), 4))),
            term_months=TERM_MONTHS[int(term_idxs[i])],
            decline_reason=None,
        ))

        if status == "funded":
            close_exit = dec_exit + timedelta(days=int(stage_days[i, 1]))
            stages.append(StageRow(app_id, "closing", dec_exit, close_exit))
            funded_at = decided_at + timedelta(days=int(fund_days[i]))
            funding_events.append(FundingEventRow(
                application_id=app_id,
                funded_at=funded_at,
                funded_amount=approved_amount,
            ))

    return OrigenceData(
        product_types=PRODUCT_TYPES,
        channels=CHANNELS,
        applications=applications,
        stages=stages,
        approvals=approvals,
        funding_events=funding_events,
    )
