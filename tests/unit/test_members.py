from synth_data.config import SynthProfile
from synth_data.generators.members import assign_member_id, generate_members

from tests.unit._synth_helpers import origence_for, symitar_for

_PROFILE = SynthProfile(
    seed=42,
    applications=500,
    approval_rate=0.72,
    funding_rate=0.85,
    member_count=3000,
)
_BRANCHES = [
    "Main Branch", "North Branch", "South Branch", "East Branch", "West Branch",
]


def test_members_deterministic() -> None:
    run1 = generate_members(_PROFILE, _BRANCHES)
    run2 = generate_members(_PROFILE, _BRANCHES)
    assert len(run1) == len(run2)
    for a, b in zip(run1, run2, strict=True):
        assert a.member_id == b.member_id
        assert a.first_name == b.first_name
        assert a.last_name == b.last_name


def test_members_count_matches_profile() -> None:
    members = generate_members(_PROFILE, _BRANCHES)
    assert len(members) == _PROFILE.member_count


def test_all_booked_loans_member_ids_in_members() -> None:
    origence = origence_for(_PROFILE)
    symitar = symitar_for(_PROFILE, origence)
    branch_names = [b.branch_name for b in symitar.branches]
    members = generate_members(_PROFILE, branch_names)
    for loan in symitar.booked_loans:
        loan.member_id = assign_member_id(loan.loan_id, members)
    member_ids = {m.member_id for m in members}
    missing = [
        loan.loan_id
        for loan in symitar.booked_loans
        if loan.member_id not in member_ids
    ]
    assert not missing, f"{len(missing)} booked_loans have member_id not in members"
