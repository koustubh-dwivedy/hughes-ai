"""Dataclasses for Origence LOS rows. Extracted from origence.py to keep
the generator under the 300-line structural cap."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


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
    applications: list["ApplicationRow"]
    stages: list["StageRow"]
    approvals: list["ApprovalRow"]
    funding_events: list["FundingEventRow"]


@dataclass
class _Arrays:
    app_uuids: list[str]
    member_picks: Any
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
