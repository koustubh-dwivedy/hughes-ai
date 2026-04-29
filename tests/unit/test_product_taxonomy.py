from collections import Counter

from synth_data.config import SynthProfile
from synth_data.generators.origence import (
    PRODUCT_SPECS,
    PRODUCT_TYPES,
    generate_origence_data,
)
from synth_data.generators.symitar import generate_symitar_data

_PROFILE = SynthProfile(
    seed=42,
    applications=500,
    approval_rate=0.72,
    funding_rate=0.85,
)


def test_all_8_products_appear_at_least_5_times() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    counts = Counter(loan.product_type_name for loan in symitar.booked_loans)
    for pt in PRODUCT_TYPES:
        assert counts[pt] >= 5, f"'{pt}' only appears {counts[pt]} times (need ≥5)"


def test_rates_within_product_spec() -> None:
    origence = generate_origence_data(_PROFILE)
    appr_map = {a.application_id: a for a in origence.approvals}
    app_map = {a.application_id: a for a in origence.applications}
    for fe in origence.funding_events:
        app = app_map[fe.application_id]
        appr = appr_map[fe.application_id]
        if appr.rate is None:
            continue
        r_lo, r_hi = PRODUCT_SPECS[app.product_type_name]["rate"]
        rate = float(appr.rate)
        assert r_lo <= rate <= r_hi + 1e-9, (
            f"{app.product_type_name}: rate {rate:.4f} outside [{r_lo}, {r_hi}]"
        )


def test_terms_within_product_spec() -> None:
    origence = generate_origence_data(_PROFILE)
    appr_map = {a.application_id: a for a in origence.approvals}
    app_map = {a.application_id: a for a in origence.applications}
    for fe in origence.funding_events:
        app = app_map[fe.application_id]
        appr = appr_map[fe.application_id]
        if appr.term_months is None:
            continue
        allowed = PRODUCT_SPECS[app.product_type_name]["terms"]
        assert appr.term_months in allowed, (
            f"{app.product_type_name}: term {appr.term_months} not in {allowed}"
        )


def test_balance_distribution_ordering() -> None:
    origence = generate_origence_data(_PROFILE)
    symitar = generate_symitar_data(origence, _PROFILE)
    amounts: dict[str, list[float]] = {pt: [] for pt in ["cre", "auto", "consumer"]}
    for loan in symitar.booked_loans:
        if loan.product_type_name in amounts:
            amounts[loan.product_type_name].append(float(loan.original_balance))
    cre_mean = sum(amounts["cre"]) / len(amounts["cre"])
    auto_mean = sum(amounts["auto"]) / len(amounts["auto"])
    consumer_mean = sum(amounts["consumer"]) / len(amounts["consumer"])
    assert cre_mean > auto_mean, (
        f"CRE mean {cre_mean:.0f} not > auto mean {auto_mean:.0f}"
    )
    assert auto_mean > consumer_mean, (
        f"auto mean {auto_mean:.0f} not > consumer mean {consumer_mean:.0f}"
    )
