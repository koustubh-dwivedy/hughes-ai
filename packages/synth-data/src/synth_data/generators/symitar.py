from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
import uuid

import numpy as np

from synth_data.config import SynthProfile
from synth_data.generators.origence import ApplicationRow, ApprovalRow, FundingEventRow, OrigenceData

BRANCH_NAMES = [
    "Main Branch", "North Branch", "South Branch", "East Branch", "West Branch",
    "Midtown Branch", "Westside Branch", "Eastside Branch", "Uptown Branch", "Downtown Branch",
]
REGIONS = ["Central", "North", "South", "East", "West"]
PAYMENT_METHODS = ["ach", "check", "online", "branch"]

_REF_DATE = datetime(2026, 4, 1, tzinfo=timezone.utc)
_REF_DATE_NAIVE = date(2026, 4, 1)


@dataclass
class BranchRow:
    branch_name: str
    region: str


@dataclass
class BookedLoanRow:
    loan_id: str
    application_id: Optional[str]
    branch_name: str
    member_id: str
    product_type_name: str
    originated_at: datetime
    original_balance: Decimal
    balance: Decimal
    rate: Decimal
    term_months: int
    maturity_at: datetime
    status: str


@dataclass
class LoanBalanceRow:
    balance_id: str
    loan_id: str
    snapshot_date: date
    balance: Decimal


@dataclass
class PaymentRow:
    payment_id: str
    loan_id: str
    paid_at: datetime
    amount: Decimal
    principal: Decimal
    interest: Decimal
    payment_method: Optional[str]


@dataclass
class DelinquencySnapshotRow:
    snapshot_id: str
    loan_id: str
    snapshot_date: date
    days_past_due: int
    delinquency_bucket: Optional[str]


@dataclass
class SymitarData:
    branches: list[BranchRow]
    booked_loans: list[BookedLoanRow]
    loan_balances: list[LoanBalanceRow]
    payments: list[PaymentRow]
    delinquency_snapshots: list[DelinquencySnapshotRow]


def _gen_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    r = annual_rate / 12
    if r == 0:
        return principal / term_months
    return principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)


def _balance_after(principal: float, annual_rate: float, term: int, months_paid: int) -> float:
    if months_paid <= 0:
        return principal
    if months_paid >= term:
        return 0.0
    r = annual_rate / 12
    if r == 0:
        return max(0.0, principal * (1 - months_paid / term))
    pmt = _monthly_payment(principal, annual_rate, term)
    return principal * (1 + r) ** months_paid - pmt * ((1 + r) ** months_paid - 1) / r


def _dpd_bucket(dpd: int) -> Optional[str]:
    if dpd <= 0:
        return None
    if dpd < 30:
        return "1-29"
    if dpd < 60:
        return "30-59"
    if dpd < 90:
        return "60-89"
    if dpd < 120:
        return "90-119"
    return "120+"


def _snapshot_date(originated_at: datetime, month_offset: int) -> date:
    y = originated_at.year + (originated_at.month - 1 + month_offset) // 12
    m = (originated_at.month - 1 + month_offset) % 12 + 1
    return date(y, m, 1)


def _payment_uuids(rng: np.random.Generator, max_term: int, m: int) -> list[list[str]]:
    raw = rng.integers(0, 256, size=(m * max_term, 16), dtype=np.uint8)
    flat = [str(uuid.UUID(bytes=bytes(raw[k]))) for k in range(m * max_term)]
    return [flat[i * max_term:(i + 1) * max_term] for i in range(m)]


def generate_symitar_data(origence: OrigenceData, profile: SynthProfile) -> SymitarData:
    rng = np.random.default_rng(profile.seed + 1)

    branches = [
        BranchRow(
            branch_name=BRANCH_NAMES[i],
            region=REGIONS[i % len(REGIONS)],
        )
        for i in range(profile.branch_count)
    ]

    funded = origence.funding_events
    m = len(funded)
    if m == 0:
        return SymitarData(branches=branches, booked_loans=[], loan_balances=[], payments=[], delinquency_snapshots=[])

    loan_uuids = _gen_uuids(rng, m)
    balance_uuid_pool = _gen_uuids(rng, m * 84)
    payment_uuid_pool = _payment_uuids(rng, 84, m)
    delinq_uuid_pool = _gen_uuids(rng, m * 12)

    orig_offset_days = rng.integers(0, 4, m)
    loan_status_r = rng.random(m)
    branch_idxs = rng.integers(0, profile.branch_count, m)
    delinq_starts = rng.integers(1, 4, m)
    pm_idxs = rng.integers(0, len(PAYMENT_METHODS), m)

    app_map: dict[str, ApplicationRow] = {a.application_id: a for a in origence.applications}
    appr_map: dict[str, ApprovalRow] = {a.application_id: a for a in origence.approvals}

    booked_loans: list[BookedLoanRow] = []
    loan_balances: list[LoanBalanceRow] = []
    payments: list[PaymentRow] = []
    delinquency_snapshots: list[DelinquencySnapshotRow] = []

    bal_uuid_idx = 0
    delinq_uuid_idx = 0

    for i, fe in enumerate(funded):
        app = app_map[fe.application_id]
        appr = appr_map[fe.application_id]

        term = int(appr.term_months) if appr.term_months else 60
        rate = float(appr.rate) if appr.rate else 0.06
        principal = float(fe.funded_amount)
        pmt = _monthly_payment(principal, rate, term)
        originated_at = fe.funded_at + timedelta(days=int(orig_offset_days[i]))
        maturity_at = originated_at + timedelta(days=term * 30)

        months_elapsed = (
            (_REF_DATE.year - originated_at.year) * 12
            + (_REF_DATE.month - originated_at.month)
        )
        matured = months_elapsed >= term
        sr = float(loan_status_r[i])

        if sr < profile.charge_off_rate:
            status = "charged_off"
            months_active = max(0, months_elapsed - 3)
        elif sr < profile.charge_off_rate + profile.dpd_30_rate:
            status = "delinquent"
            months_active = months_elapsed
        elif matured:
            status = "paid_off"
            months_active = term
        else:
            status = "current"
            months_active = months_elapsed

        current_balance = 0.0 if status == "paid_off" else _balance_after(principal, rate, term, months_active)
        branch_name = BRANCH_NAMES[int(branch_idxs[i])]

        booked_loans.append(BookedLoanRow(
            loan_id=loan_uuids[i],
            application_id=fe.application_id,
            branch_name=branch_name,
            member_id=app.member_id,
            product_type_name=app.product_type_name,
            originated_at=originated_at,
            original_balance=Decimal(str(round(principal, 2))),
            balance=Decimal(str(round(current_balance, 2))),
            rate=Decimal(str(round(rate, 4))),
            term_months=term,
            maturity_at=maturity_at,
            status=status,
        ))

        r_monthly = rate / 12
        running_bal = principal
        for mo in range(1, months_active + 1):
            snap_date = _snapshot_date(originated_at, mo)
            interest_part = running_bal * r_monthly
            principal_part = min(pmt - interest_part, running_bal)
            running_bal = max(0.0, running_bal - principal_part)

            loan_balances.append(LoanBalanceRow(
                balance_id=balance_uuid_pool[bal_uuid_idx % len(balance_uuid_pool)],
                loan_id=loan_uuids[i],
                snapshot_date=snap_date,
                balance=Decimal(str(round(running_bal, 2))),
            ))
            bal_uuid_idx += 1

            missed_months = int(delinq_starts[i]) if status in ("delinquent", "charged_off") else 0
            if mo <= months_active - missed_months:
                payments.append(PaymentRow(
                    payment_id=payment_uuid_pool[i][mo - 1],
                    loan_id=loan_uuids[i],
                    paid_at=originated_at + timedelta(days=mo * 30),
                    amount=Decimal(str(round(pmt, 2))),
                    principal=Decimal(str(round(principal_part, 2))),
                    interest=Decimal(str(round(interest_part, 2))),
                    payment_method=PAYMENT_METHODS[int(pm_idxs[i])],
                ))

        if status in ("delinquent", "charged_off"):
            missed = int(delinq_starts[i])
            for k in range(missed):
                dpd = (k + 1) * 30
                snap_date = _snapshot_date(originated_at, months_active - missed + k + 1)
                delinquency_snapshots.append(DelinquencySnapshotRow(
                    snapshot_id=delinq_uuid_pool[delinq_uuid_idx % len(delinq_uuid_pool)],
                    loan_id=loan_uuids[i],
                    snapshot_date=snap_date,
                    days_past_due=dpd,
                    delinquency_bucket=_dpd_bucket(dpd),
                ))
                delinq_uuid_idx += 1

    return SymitarData(
        branches=branches,
        booked_loans=booked_loans,
        loan_balances=loan_balances,
        payments=payments,
        delinquency_snapshots=delinquency_snapshots,
    )
