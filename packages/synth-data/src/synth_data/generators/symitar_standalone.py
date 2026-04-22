import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from synth_data.generators.symitar_types import BookedLoanRow, BranchRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_TERM_MONTHS = [24, 36, 48, 60, 72]
_STATUSES = ["current", "delinquent", "paid_off", "charged_off"]
_STATUS_WEIGHTS = [0.70, 0.15, 0.10, 0.05]


def _fresh_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw: Any = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def generate_standalone_loans(
    rng: np.random.Generator,
    count: int,
    member_pool: list[str],
    product_types: list[str],
    branches: list[BranchRow],
) -> list[BookedLoanRow]:
    """Generate branch-originated loans not linked to any LOS application.

    First half samples member_ids from member_pool (ambiguous candidates);
    second half uses fresh UUIDs (unmatched).
    """
    half = count // 2
    ambiguous_members = [member_pool[i % len(member_pool)] for i in range(half)]
    fresh_members = _fresh_uuids(rng, count - half)
    all_members = ambiguous_members + fresh_members

    loan_ids = _fresh_uuids(rng, count)
    balances = rng.integers(5_000, 60_000, count).tolist()
    rates = rng.uniform(0.04, 0.18, count).tolist()
    term_idxs = rng.integers(0, len(_TERM_MONTHS), count).tolist()
    orig_days_ago = rng.integers(180, 730, count).tolist()
    pt_idxs = rng.integers(0, len(product_types), count).tolist()
    br_idxs = rng.integers(0, len(branches), count).tolist()
    status_choices = rng.choice(
        len(_STATUSES), count, p=_STATUS_WEIGHTS
    ).tolist()

    loans = []
    for i in range(count):
        term = _TERM_MONTHS[int(term_idxs[i])]
        orig = _REF_DATE - timedelta(days=int(orig_days_ago[i]))
        maturity = orig + timedelta(days=term * 30)
        principal = Decimal(str(balances[i]))
        loans.append(BookedLoanRow(
            loan_id=loan_ids[i],
            application_id=None,
            branch_name=branches[int(br_idxs[i])].branch_name,
            member_id=all_members[i],
            product_type_name=product_types[int(pt_idxs[i])],
            originated_at=orig,
            original_balance=principal,
            balance=principal,
            rate=Decimal(str(round(float(rates[i]), 4))),
            term_months=term,
            maturity_at=maturity,
            status=_STATUSES[int(status_choices[i])],
        ))
    return loans
