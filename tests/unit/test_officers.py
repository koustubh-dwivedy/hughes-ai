from collections import defaultdict

from synth_data.config import SynthProfile
from synth_data.generators.officers import generate_officers

from tests.unit._synth_helpers import origence_for, symitar_for

_PROFILE = SynthProfile(
    seed=42,
    applications=500,
    approval_rate=0.72,
    funding_rate=0.85,
    officer_count=20,
)
_BRANCHES = [
    "Main Branch", "North Branch", "South Branch", "East Branch", "West Branch",
]


def test_all_booked_loans_have_officer_id() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    missing = [loan.loan_id for loan in symitar.booked_loans if loan.officer_id is None]
    assert not missing, f"{len(missing)} booked_loans have no officer_id"


def test_every_branch_has_at_least_3_active_officers() -> None:
    officers = generate_officers(_PROFILE, _BRANCHES)
    active_by_branch: dict[str, int] = defaultdict(int)
    for o in officers:
        if o.status == "active":
            active_by_branch[o.branch_name] += 1
    for branch in _BRANCHES:
        assert active_by_branch[branch] >= 3, (
            f"{branch} has only {active_by_branch[branch]} active officer(s)"
        )


def test_departed_officers_still_own_loans() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    departed_ids = {o.officer_id for o in symitar.officers if o.status == "departed"}
    assert departed_ids, "no departed officers generated"
    loan_officer_ids = {loan.officer_id for loan in symitar.booked_loans}
    assert departed_ids & loan_officer_ids, "no loan is assigned to a departed officer"


def test_officers_deterministic() -> None:
    run1 = generate_officers(_PROFILE, _BRANCHES)
    run2 = generate_officers(_PROFILE, _BRANCHES)
    assert len(run1) == len(run2)
    for a, b in zip(run1, run2, strict=True):
        assert a.officer_id == b.officer_id
        assert a.name == b.name
        assert a.status == b.status
