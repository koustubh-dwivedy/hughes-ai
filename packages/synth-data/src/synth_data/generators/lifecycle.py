"""Generate one lifecycle event per (loan, month)."""

import uuid
from datetime import UTC, date, datetime

import numpy as np

from synth_data.generators.symitar_types import BookedLoanRow, LoanLifecycleEventRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_RENEWED_RATE = 0.05


def _first_of_month(yr: int, mo: int) -> date:
    return date(yr, mo, 1)


def generate_lifecycle_events(
    loans: list[BookedLoanRow],
    seed: int,
) -> list[LoanLifecycleEventRow]:
    rng = np.random.default_rng(seed + 99)
    events: list[LoanLifecycleEventRow] = []
    for loan in loans:
        orig = loan.originated_at
        start_yr, start_mo = orig.year, orig.month
        ref_yr, ref_mo = _REF_DATE.year, _REF_DATE.month
        months_active = (ref_yr - start_yr) * 12 + (ref_mo - start_mo)
        if loan.status == "paid_off":
            months_active = loan.term_months
        months_active = max(1, months_active)
        renew_mo = (
            int(rng.integers(2, months_active))
            if months_active > 2 and rng.random() < _RENEWED_RATE
            else -1
        )
        raw = rng.integers(0, 256, (months_active, 16), dtype=np.uint8)
        event_ids = [str(uuid.UUID(bytes=bytes(row))) for row in raw]
        for idx in range(months_active):
            mo_offset = start_mo - 1 + idx
            yr = start_yr + mo_offset // 12
            mo = mo_offset % 12 + 1
            if idx == 0:
                etype = "new"
            elif idx == renew_mo:
                etype = "renewed"
            elif idx == months_active - 1 and loan.status == "paid_off":
                etype = "paid_off"
            else:
                etype = "active"
            events.append(LoanLifecycleEventRow(
                event_id=event_ids[idx],
                loan_id=loan.loan_id,
                event_month=_first_of_month(yr, mo),
                event_type=etype,
            ))
    return events
