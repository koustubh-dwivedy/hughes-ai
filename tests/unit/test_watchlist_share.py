from datetime import UTC, datetime
from decimal import Decimal

import numpy as np

from synth_data.generators.symitar_types import BookedLoanRow
from synth_data.generators.watchlist import generate_watchlist

_DT = datetime(2025, 1, 1, tzinfo=UTC)
_MAT = datetime(2030, 1, 1, tzinfo=UTC)


def _current_loans(n: int) -> list[BookedLoanRow]:
    return [
        BookedLoanRow(
            loan_id=f"loan-{i:04d}", application_id=None, branch_name="A",
            member_id=f"mem-{i:04d}", product_type_name="Auto",
            originated_at=_DT, original_balance=Decimal("10000"),
            balance=Decimal("9000"), rate=Decimal("0.05"), term_months=60,
            maturity_at=_MAT, status="current", officer_id=None, is_nonaccrual=False,
        )
        for i in range(n)
    ]


def test_watchlist_count_matches_share() -> None:
    loans = _current_loans(100)
    result = generate_watchlist(np.random.default_rng(42), loans, watchlist_share=0.10)
    assert len(result) == max(1, round(100 * 0.10))


def test_watchlist_default_share_is_four_percent() -> None:
    loans = _current_loans(100)
    result = generate_watchlist(np.random.default_rng(42), loans)
    assert len(result) == max(1, round(100 * 0.04))
