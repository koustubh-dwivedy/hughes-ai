from collections import Counter
from datetime import date

from synth_data.config import SynthProfile

from tests.unit._synth_helpers import origence_for, symitar_for

_PROFILE = SynthProfile(
    seed=42,
    applications=500,
    approval_rate=0.72,
    funding_rate=0.85,
    history_months=26,
)


def test_oldest_balance_row_within_26_months() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    oldest = min(r.snapshot_date for r in symitar.loan_balances)
    assert oldest >= date(2024, 1, 1), f"oldest balance {oldest} before 26-month window"


def test_each_loan_has_lifecycle_events() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    loan_ids = {ln.loan_id for ln in symitar.booked_loans}
    event_loan_ids = {e.loan_id for e in symitar.loan_lifecycle_events}
    missing = loan_ids - event_loan_ids
    assert not missing, f"{len(missing)} loans have no lifecycle events"


def test_paid_off_loans_have_paid_off_event() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    paid_off = {ln.loan_id for ln in symitar.booked_loans if ln.status == "paid_off"}
    events_by_loan: dict[str, set[str]] = {}
    for e in symitar.loan_lifecycle_events:
        events_by_loan.setdefault(e.loan_id, set()).add(e.event_type)
    for loan_id in paid_off:
        assert "paid_off" in events_by_loan.get(loan_id, set()), (
            f"paid_off loan {loan_id} missing 'paid_off' event"
        )


def test_each_loan_has_exactly_one_new_event() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    new_counts: Counter[str] = Counter(
        e.loan_id for e in symitar.loan_lifecycle_events if e.event_type == "new"
    )
    multi = [lid for lid, cnt in new_counts.items() if cnt != 1]
    assert not multi, f"{len(multi)} loans have != 1 'new' event"
