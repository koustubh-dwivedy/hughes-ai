"""Amortization + delinquency helpers extracted from symitar.py.

Kept as a separate module so symitar.py stays under the 300-line structural
cap while the dollars-and-cents math sits in one place.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from synth_data.generators.symitar_types import (
    DelinquencySnapshotRow,
    LoanBalanceRow,
    PaymentRow,
)

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)

_DPD_BUCKETS = [
    (14, "1-14"), (29, "15-29"), (59, "30-59"), (89, "60-89"), (119, "90-119"),
]


def gen_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    r = annual_rate / 12
    if r == 0:
        return principal / term_months
    return principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)


def balance_after(
    principal: float, annual_rate: float, term: int, months_paid: int
) -> float:
    if months_paid <= 0:
        return principal
    if months_paid >= term:
        return 0.0
    r = annual_rate / 12
    if r == 0:
        return max(0.0, principal * (1 - months_paid / term))
    pmt = monthly_payment(principal, annual_rate, term)
    return principal * (1 + r) ** months_paid - pmt * ((1 + r) ** months_paid - 1) / r


def dpd_bucket(dpd: int) -> str | None:
    if dpd <= 0:
        return None
    for bound, label in _DPD_BUCKETS:
        if dpd <= bound:
            return label
    return "120+"


def snapshot_date(originated_at: datetime, month_offset: int) -> date:
    y = originated_at.year + (originated_at.month - 1 + month_offset) // 12
    m = (originated_at.month - 1 + month_offset) % 12 + 1
    return date(y, m, 1)


def months_elapsed(originated_at: datetime) -> int:
    return (
        (_REF_DATE.year - originated_at.year) * 12
        + (_REF_DATE.month - originated_at.month)
    )


def build_amortization(
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
        snap = snapshot_date(originated_at, mo)
        interest_part = running_bal * r_monthly
        principal_part = min(pmt - interest_part, running_bal)
        running_bal = max(0.0, running_bal - principal_part)
        balances.append(LoanBalanceRow(
            balance_id=bal_pool[bal_idx % len(bal_pool)],
            loan_id=loan_id, snapshot_date=snap,
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


def build_delinquency(
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
            snapshot_date=snapshot_date(originated_at, mo),
            days_past_due=dpd,
            delinquency_bucket=dpd_bucket(dpd),
        ))
        delinq_idx += 1
    return rows, delinq_idx


def loan_status_after(
    sr: float, charge_off_rate: float, dpd_30_rate: float,
    months: int, term: int,
) -> tuple[str, int]:
    if sr < charge_off_rate:
        return "charged_off", max(0, months - 3)
    if sr < charge_off_rate + dpd_30_rate:
        return "delinquent", months
    if months >= term:
        return "paid_off", term
    return "current", months


def sample_loan_arrays(
    rng: np.random.Generator, m: int, branch_count: int,
    payment_methods_count: int,
) -> dict[str, Any]:
    """Pre-generate arrays for vectorized loan building."""
    max_term = 84
    raw = rng.integers(0, 256, size=(m * max_term, 16), dtype=np.uint8)
    flat = [str(uuid.UUID(bytes=bytes(raw[k]))) for k in range(m * max_term)]
    pmt_pool = [flat[i * max_term:(i + 1) * max_term] for i in range(m)]
    return {
        "loan_uuids": gen_uuids(rng, m),
        "bal_pool": gen_uuids(rng, m * max_term),
        "pmt_pool": pmt_pool,
        "delinq_pool": gen_uuids(rng, m * 12),
        "orig_offset": rng.integers(0, 4, m),
        "status_r": rng.random(m),
        "branch_idxs": rng.integers(0, branch_count, m),
        "delinq_starts": rng.integers(1, 5, m),
        "pm_idxs": rng.integers(0, payment_methods_count, m),
    }
