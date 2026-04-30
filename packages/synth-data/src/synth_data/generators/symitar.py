import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from synth_data.config import SynthProfile
from synth_data.generators.lifecycle import generate_lifecycle_events
from synth_data.generators.officers import assign_officer_id, generate_officers
from synth_data.generators.origence import (
    PRODUCT_SPECS,
    ApplicationRow,
    ApprovalRow,
    FundingEventRow,
    OrigenceData,
)
from synth_data.generators.symitar_standalone import generate_standalone_loans
from synth_data.generators.symitar_types import (
    BookedLoanRow,
    BranchRow,
    DelinquencySnapshotRow,
    LoanBalanceRow,
    PaymentRow,
    SymitarData,
)

BRANCH_NAMES = [
    "Main Branch", "North Branch", "South Branch", "East Branch", "West Branch",
    "Midtown Branch", "Westside Branch", "Eastside Branch",
    "Uptown Branch", "Downtown Branch",
]
REGIONS = ["Central", "North", "South", "East", "West"]
PAYMENT_METHODS = ["ach", "check", "online", "branch"]

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)


@dataclass
class _LoanArrays:
    loan_uuids: list[str]
    bal_pool: list[str]
    pmt_pool: list[list[str]]
    delinq_pool: list[str]
    orig_offset: Any
    status_r: Any
    branch_idxs: Any
    delinq_starts: Any
    pm_idxs: Any


def _gen_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    r = annual_rate / 12
    if r == 0:
        return principal / term_months
    return principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)


def _balance_after(
    principal: float, annual_rate: float, term: int, months_paid: int
) -> float:
    if months_paid <= 0:
        return principal
    if months_paid >= term:
        return 0.0
    r = annual_rate / 12
    if r == 0:
        return max(0.0, principal * (1 - months_paid / term))
    pmt = _monthly_payment(principal, annual_rate, term)
    return principal * (1 + r) ** months_paid - pmt * ((1 + r) ** months_paid - 1) / r


_DPD_BUCKETS = [
    (14, "1-14"), (29, "15-29"), (59, "30-59"), (89, "60-89"), (119, "90-119"),
]


def _dpd_bucket(dpd: int) -> str | None:
    if dpd <= 0:
        return None
    for bound, label in _DPD_BUCKETS:
        if dpd <= bound:
            return label
    return "120+"


def _snapshot_date(originated_at: datetime, month_offset: int) -> date:
    y = originated_at.year + (originated_at.month - 1 + month_offset) // 12
    m = (originated_at.month - 1 + month_offset) % 12 + 1
    return date(y, m, 1)


def _sample_loan_arrays(
    rng: np.random.Generator, m: int, branch_count: int
) -> _LoanArrays:
    max_term = 84
    raw = rng.integers(0, 256, size=(m * max_term, 16), dtype=np.uint8)
    flat = [str(uuid.UUID(bytes=bytes(raw[k]))) for k in range(m * max_term)]
    pmt_pool = [flat[i * max_term:(i + 1) * max_term] for i in range(m)]
    return _LoanArrays(
        loan_uuids=_gen_uuids(rng, m),
        bal_pool=_gen_uuids(rng, m * max_term),
        pmt_pool=pmt_pool,
        delinq_pool=_gen_uuids(rng, m * 12),
        orig_offset=rng.integers(0, 4, m),
        status_r=rng.random(m),
        branch_idxs=rng.integers(0, branch_count, m),
        delinq_starts=rng.integers(1, 5, m),
        pm_idxs=rng.integers(0, len(PAYMENT_METHODS), m),
    )


def _build_amortization(
    loan_id: str,
    originated_at: datetime,
    principal: float,
    rate: float,
    term: int,
    months_active: int,
    pmt: float,
    missed: int,
    bal_pool: list[str],
    pmt_pool_i: list[str],
    bal_idx: int,
    pm_method: str,
) -> tuple[list[LoanBalanceRow], list[PaymentRow], int]:
    r_monthly = rate / 12
    running_bal = principal
    balances: list[LoanBalanceRow] = []
    payments: list[PaymentRow] = []
    for mo in range(1, months_active + 1):
        snap_date = _snapshot_date(originated_at, mo)
        interest_part = running_bal * r_monthly
        principal_part = min(pmt - interest_part, running_bal)
        running_bal = max(0.0, running_bal - principal_part)
        balances.append(LoanBalanceRow(
            balance_id=bal_pool[bal_idx % len(bal_pool)],
            loan_id=loan_id, snapshot_date=snap_date,
            balance=Decimal(str(round(running_bal, 2))),
        ))
        bal_idx += 1
        if mo <= months_active - missed:
            payments.append(PaymentRow(
                payment_id=pmt_pool_i[mo - 1], loan_id=loan_id,
                paid_at=originated_at + timedelta(days=mo * 30),
                amount=Decimal(str(round(pmt, 2))),
                principal=Decimal(str(round(principal_part, 2))),
                interest=Decimal(str(round(interest_part, 2))),
                payment_method=pm_method,
            ))
    return balances, payments, bal_idx


def _build_delinquency(
    loan_id: str,
    originated_at: datetime,
    months_active: int,
    missed: int,
    delinq_pool: list[str],
    delinq_idx: int,
) -> tuple[list[DelinquencySnapshotRow], int]:
    rows: list[DelinquencySnapshotRow] = []
    dpd_start = int(loan_id[0], 16) * 2 % 29 + 1
    for k in range(missed):
        dpd = dpd_start + k * 30
        mo = months_active - missed + k + 1
        rows.append(DelinquencySnapshotRow(
            snapshot_id=delinq_pool[delinq_idx % len(delinq_pool)],
            loan_id=loan_id,
            snapshot_date=_snapshot_date(originated_at, mo),
            days_past_due=dpd,
            delinquency_bucket=_dpd_bucket(dpd),
        ))
        delinq_idx += 1
    return rows, delinq_idx


def _loan_status(
    sr: float, profile: SynthProfile, months_elapsed: int, term: int
) -> tuple[str, int]:
    if sr < profile.charge_off_rate:
        return "charged_off", max(0, months_elapsed - 3)
    if sr < profile.charge_off_rate + profile.dpd_30_rate:
        return "delinquent", months_elapsed
    if months_elapsed >= term:
        return "paid_off", term
    return "current", months_elapsed


_LoanResult = tuple[
    BookedLoanRow, list[LoanBalanceRow], list[PaymentRow],
    list[DelinquencySnapshotRow], int, int,
]


def _build_loan(
    i: int,
    fe: FundingEventRow,
    app: ApplicationRow,
    appr: ApprovalRow,
    profile: SynthProfile,
    a: _LoanArrays,
    bal_idx: int,
    delinq_idx: int,
) -> _LoanResult:
    _spec = PRODUCT_SPECS[app.product_type_name]
    term = int(appr.term_months) if appr.term_months else _spec["terms"][0]
    rate = float(appr.rate) if appr.rate else _spec["rate"][0]
    principal = float(fe.funded_amount)
    pmt = _monthly_payment(principal, rate, term)
    originated_at = fe.funded_at + timedelta(days=int(a.orig_offset[i]))
    maturity_at = originated_at + timedelta(days=term * 30)
    months_elapsed = (
        (_REF_DATE.year - originated_at.year) * 12
        + (_REF_DATE.month - originated_at.month)
    )
    status, ma = _loan_status(float(a.status_r[i]), profile, months_elapsed, term)
    cur_bal = 0.0 if status == "paid_off" else _balance_after(principal, rate, term, ma)
    is_bad = status in ("delinquent", "charged_off")
    missed = int(a.delinq_starts[i]) if is_bad else 0
    _dpd = max(0, int(a.loan_uuids[i][0], 16)*2%29 + (missed-1)*30 + 1) * bool(missed)
    nonaccrual = _dpd >= 90 or status == "charged_off"
    loan = BookedLoanRow(
        loan_id=a.loan_uuids[i], application_id=fe.application_id,
        branch_name=BRANCH_NAMES[int(a.branch_idxs[i])],
        member_id=app.member_id, product_type_name=app.product_type_name,
        originated_at=originated_at, original_balance=Decimal(str(round(principal, 2))),
        balance=Decimal(str(round(cur_bal, 2))), rate=Decimal(str(round(rate, 4))),
        term_months=term, maturity_at=maturity_at, status=status,
        is_nonaccrual=nonaccrual,
    )
    pm = PAYMENT_METHODS[int(a.pm_idxs[i])]
    lb, p, bal_idx = _build_amortization(
        a.loan_uuids[i], originated_at, principal, rate,
        term, ma, pmt, missed, a.bal_pool, a.pmt_pool[i], bal_idx, pm,
    )
    drows: list[DelinquencySnapshotRow] = []
    if missed > 0:
        drows, delinq_idx = _build_delinquency(
            a.loan_uuids[i], originated_at, ma, missed, a.delinq_pool, delinq_idx,
        )
    return loan, lb, p, drows, bal_idx, delinq_idx


def generate_symitar_data(origence: OrigenceData, profile: SynthProfile) -> SymitarData:
    rng = np.random.default_rng(profile.seed + 1)
    branches = [
        BranchRow(branch_name=BRANCH_NAMES[i], region=REGIONS[i % len(REGIONS)])
        for i in range(profile.branch_count)
    ]
    funded = origence.funding_events
    m = len(funded)
    if m == 0:
        return SymitarData(
            branches=branches, booked_loans=[], loan_balances=[],
            payments=[], delinquency_snapshots=[],
        )
    arrays = _sample_loan_arrays(rng, m, profile.branch_count)
    app_map: dict[str, ApplicationRow] = {
        a.application_id: a for a in origence.applications
    }
    appr_map: dict[str, ApprovalRow] = {
        a.application_id: a for a in origence.approvals
    }
    booked: list[BookedLoanRow] = []
    bals: list[LoanBalanceRow] = []
    pmts: list[PaymentRow] = []
    drows: list[DelinquencySnapshotRow] = []
    bal_idx = delinq_idx = 0
    for i, fe in enumerate(funded):
        app = app_map[fe.application_id]
        appr = appr_map[fe.application_id]
        loan, lb, p, d, bal_idx, delinq_idx = _build_loan(
            i, fe, app, appr, profile, arrays, bal_idx, delinq_idx,
        )
        booked.append(loan)
        bals.extend(lb)
        pmts.extend(p)
        drows.extend(d)
    member_pool = [a.member_id for a in origence.applications if a.status == "funded"]
    standalone = generate_standalone_loans(
        rng, profile.standalone_loan_count,
        member_pool, origence.product_types, branches,
    )
    officers = generate_officers(profile, [b.branch_name for b in branches])
    all_loans = booked + standalone
    for loan in all_loans:
        loan.officer_id = assign_officer_id(loan.loan_id, loan.branch_name, officers)
    lifecycle_events = generate_lifecycle_events(all_loans, profile.seed)
    return SymitarData(
        branches=branches, booked_loans=all_loans, loan_balances=bals,
        payments=pmts, delinquency_snapshots=drows, officers=officers,
        loan_lifecycle_events=lifecycle_events,
    )
