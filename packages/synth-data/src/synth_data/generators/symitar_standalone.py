import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from synth_data.config import LoanProductSpec, ProductCatalog
from synth_data.generators.symitar_types import BookedLoanRow, BranchRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_STATUSES = ["current", "delinquent", "paid_off", "charged_off"]
_STATUS_WEIGHTS = [0.70, 0.15, 0.10, 0.05]


def _fresh_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw: Any = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _build_standalone_loan(
    rng: np.random.Generator,
    loan_id: str,
    member_id: str,
    spec: "LoanProductSpec",
    branch_name: str,
    days_ago: int,
    status: str,
) -> BookedLoanRow:
    amount_lo, amount_hi = spec.amount_range
    rate_lo, rate_hi = spec.rate_range
    amount = float(rng.uniform(amount_lo, amount_hi))
    rate = float(rng.uniform(rate_lo, rate_hi)) if rate_lo < rate_hi else rate_lo
    term = int(rng.choice(spec.term_months)) if spec.term_months else 60
    orig = _REF_DATE - timedelta(days=days_ago)
    maturity = orig + timedelta(days=term * 30)
    principal = Decimal(str(round(amount, 2)))
    return BookedLoanRow(
        loan_id=loan_id,
        application_id=None,
        branch_name=branch_name,
        member_id=member_id,
        product_type_name=spec.code,
        originated_at=orig,
        original_balance=principal,
        balance=principal,
        rate=Decimal(str(round(rate, 4))),
        term_months=term,
        maturity_at=maturity,
        status=status,
        is_nonaccrual=(status == "charged_off"),
    )


def generate_standalone_loans(
    rng: np.random.Generator,
    count: int,
    member_pool: list[str],
    catalog: ProductCatalog,
    branches: list[BranchRow],
) -> list[BookedLoanRow]:
    """Generate branch-originated loans not linked to any LOS application.

    First half samples member_ids from member_pool (ambiguous candidates);
    second half uses fresh UUIDs (unmatched). Excludes credit_card and
    auto_indirect — both need workflows that don't fit standalone bookings.
    """
    if count <= 0:
        return []
    eligible = [
        p for p in catalog.loan_products
        if p.code not in {"credit_card", "auto_indirect"}
    ]
    if not eligible:
        return []
    half = count // 2
    ambiguous = (
        [member_pool[i % len(member_pool)] for i in range(half)]
        if member_pool else []
    )
    fresh = _fresh_uuids(rng, count - len(ambiguous))
    all_members = ambiguous + fresh
    loan_ids = _fresh_uuids(rng, count)
    pt_idxs = rng.integers(0, len(eligible), count).tolist()
    br_idxs = rng.integers(0, len(branches), count).tolist()
    status_choices = rng.choice(
        len(_STATUSES), count, p=_STATUS_WEIGHTS,
    ).tolist()
    days_ago = rng.integers(180, 730, count).tolist()
    return [
        _build_standalone_loan(
            rng, loan_ids[i], all_members[i],
            eligible[int(pt_idxs[i])],
            branches[int(br_idxs[i])].branch_name,
            int(days_ago[i]), _STATUSES[int(status_choices[i])],
        )
        for i in range(count)
    ]
