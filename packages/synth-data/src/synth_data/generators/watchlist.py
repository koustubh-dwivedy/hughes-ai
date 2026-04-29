import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np

from synth_data.generators.symitar_types import BookedLoanRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_WATCHLIST_REASONS = [
    "payment_concern", "covenant_breach", "industry_risk",
    "collateral_decline", "management_change",
]


@dataclass
class WatchlistRow:
    watchlist_id: str
    loan_id: str
    added_at: datetime
    removed_at: datetime | None
    reason: str


def generate_watchlist(
    rng: np.random.Generator,
    booked_loans: list[BookedLoanRow],
) -> list[WatchlistRow]:
    active = [
        loan for loan in booked_loans
        if loan.status in ("current", "delinquent")
    ]
    n = max(1, round(len(active) * 0.04))
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    ids = [str(uuid.UUID(bytes=bytes(raw[k]))) for k in range(n)]
    choices = rng.choice(len(active), size=n, replace=False)
    reasons = rng.integers(0, len(_WATCHLIST_REASONS), n)
    days_ago = rng.integers(30, 365, n)
    still_on = rng.random(n) < 0.80
    rows: list[WatchlistRow] = []
    for i in range(n):
        added = _REF_DATE - timedelta(days=int(days_ago[i]))
        removed = None if still_on[i] else added + timedelta(days=int(days_ago[i]) // 2)
        rows.append(WatchlistRow(
            watchlist_id=ids[i],
            loan_id=active[choices[i]].loan_id,
            added_at=added,
            removed_at=removed,
            reason=_WATCHLIST_REASONS[int(reasons[i])],
        ))
    return rows
