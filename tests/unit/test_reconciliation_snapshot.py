from synth_data.config import SynthProfile
from synth_data.generators.origence import generate_origence_data
from synth_data.generators.symitar import generate_symitar_data
from synth_data.reconciliation import reconcile

_PROFILE = SynthProfile(
    seed=42, applications=500, approval_rate=0.72, funding_rate=0.85,
)


def test_reconcile_covers_all_booked_loans() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    rows = reconcile(origence, symitar)
    loan_ids_in = {ln.loan_id for ln in symitar.booked_loans}
    loan_ids_out = {r.loan_id for r in rows}
    assert loan_ids_in == loan_ids_out


def test_reconcile_only_valid_match_types() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    rows = reconcile(origence, symitar)
    valid = {"matched", "ambiguous", "unmatched"}
    assert all(r.match_type in valid for r in rows)


def test_reconcile_snapshot_counts() -> None:
    """Snapshot: exact match/ambiguous/unmatched counts must not drift.

    Deposits (added in A4b) must not affect these counts — if they do,
    reconcile() has accidentally started including deposit rows.
    """
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    rows = reconcile(origence, symitar)
    counts = {mt: sum(1 for r in rows if r.match_type == mt)
              for mt in ("matched", "ambiguous", "unmatched")}
    assert counts == {"matched": 291, "ambiguous": 5, "unmatched": 5}
