import numpy as np
from synth_data.config import SynthProfile
from synth_data.generators.origence import generate_origence_data
from synth_data.generators.symitar import _dpd_bucket, generate_symitar_data
from synth_data.generators.watchlist import generate_watchlist

_PROFILE = SynthProfile(
    seed=42,
    applications=500,
    approval_rate=0.72,
    funding_rate=0.85,
)

_BOUNDARIES = [
    (0, None), (1, "1-14"), (14, "1-14"), (15, "15-29"), (29, "15-29"),
    (30, "30-59"), (59, "30-59"), (60, "60-89"), (89, "60-89"),
    (90, "90-119"), (119, "90-119"), (120, "120+"), (9999, "120+"),
]


def test_dpd_bucket_boundaries() -> None:
    for dpd, expected in _BOUNDARIES:
        assert _dpd_bucket(dpd) == expected, (
            f"_dpd_bucket({dpd}) = {_dpd_bucket(dpd)!r}"
        )


def test_dpd_bucket_property_all_integers_0_to_365() -> None:
    rng = np.random.default_rng(0)
    sample = rng.integers(0, 366, 1200)
    for val in sample:
        bucket = _dpd_bucket(int(val))
        if val <= 0:
            assert bucket is None
        else:
            assert bucket is not None, f"dpd={val} returned None"


def test_bucket_contract_matches_generated_snapshots() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    for row in symitar.delinquency_snapshots:
        expected = _dpd_bucket(row.days_past_due)
        assert row.delinquency_bucket == expected, (
            f"loan {row.loan_id}: bucket={row.delinquency_bucket!r}, "
            f"_dpd_bucket({row.days_past_due})={expected!r}"
        )


def test_both_new_buckets_appear_in_snapshots() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    buckets = {r.delinquency_bucket for r in symitar.delinquency_snapshots}
    assert "1-14" in buckets, "no '1-14' bucket rows generated"
    assert "15-29" in buckets, "no '15-29' bucket rows generated"


def test_is_nonaccrual_derivation() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    snap_dpd = {}
    for row in symitar.delinquency_snapshots:
        snap_dpd[row.loan_id] = max(snap_dpd.get(row.loan_id, 0), row.days_past_due)
    for loan in symitar.booked_loans:
        dpd = snap_dpd.get(loan.loan_id, 0)
        expected = dpd >= 90 or loan.status == "charged_off"
        assert loan.is_nonaccrual == expected, (
            f"loan {loan.loan_id}: is_nonaccrual={loan.is_nonaccrual}, "
            f"status={loan.status}, max_dpd={dpd}"
        )


def test_nonaccrual_loans_not_current() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    bad = [
        loan for loan in symitar.booked_loans
        if loan.is_nonaccrual and loan.status == "current"
    ]
    assert not bad, f"{len(bad)} nonaccrual loans have status='current'"


def test_watchlist_coverage_3_to_5_percent() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    rng = np.random.default_rng(_PROFILE.seed + 30)
    wl = generate_watchlist(rng, symitar.booked_loans)
    active_count = sum(
        1 for loan in symitar.booked_loans if loan.status in ("current", "delinquent")
    )
    pct = len(wl) / active_count
    assert 0.03 <= pct <= 0.05, (
        f"watchlist coverage {pct:.1%} outside [3%, 5%] "
        f"({len(wl)} entries / {active_count} active loans)"
    )
