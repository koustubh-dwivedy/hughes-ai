"""Smoke tests for the new 6-product loan taxonomy (HUG-162).

Every product appears at least N times. Rates and terms stay within the
spec ranges declared in packages/synth-data/profiles/products.yaml.
The expected balance ordering reflects the new taxonomy:
mortgages > autos > credit cards (since mortgages dwarf the others).
"""

from collections import Counter

from synth_data.config import ProductCatalog, SynthProfile
from synth_data.generators.members import MemberRow
from synth_data.generators.origence import generate_origence_data
from synth_data.generators.symitar import generate_symitar_data


def test_every_product_appears(
    profile: SynthProfile,
    catalog: ProductCatalog,
    members: list[MemberRow],
) -> None:
    origence = generate_origence_data(profile, catalog, members)
    symitar = generate_symitar_data(origence, profile, catalog)
    counts = Counter(loan.product_type_name for loan in symitar.booked_loans)
    for spec in catalog.loan_products:
        assert counts[spec.code] >= 5, (
            f"'{spec.code}' only appears {counts[spec.code]} times (need >= 5)"
        )


def test_rates_within_spec(
    profile: SynthProfile,
    catalog: ProductCatalog,
    members: list[MemberRow],
) -> None:
    origence = generate_origence_data(profile, catalog, members)
    spec_by_code = {p.code: p for p in catalog.loan_products}
    appr_map = {a.application_id: a for a in origence.approvals}
    app_map = {a.application_id: a for a in origence.applications}
    for fe in origence.funding_events:
        app = app_map[fe.application_id]
        appr = appr_map[fe.application_id]
        if appr.rate is None:
            continue
        spec = spec_by_code[app.product_type_name]
        r_lo, r_hi = spec.rate_range
        rate = float(appr.rate)
        assert r_lo <= rate <= r_hi + 1e-9, (
            f"{app.product_type_name}: rate {rate:.4f} outside [{r_lo}, {r_hi}]"
        )


def test_terms_within_spec(
    profile: SynthProfile,
    catalog: ProductCatalog,
    members: list[MemberRow],
) -> None:
    origence = generate_origence_data(profile, catalog, members)
    spec_by_code = {p.code: p for p in catalog.loan_products}
    appr_map = {a.application_id: a for a in origence.approvals}
    app_map = {a.application_id: a for a in origence.applications}
    for fe in origence.funding_events:
        app = app_map[fe.application_id]
        appr = appr_map[fe.application_id]
        if appr.term_months is None:
            continue
        spec = spec_by_code[app.product_type_name]
        assert appr.term_months in spec.term_months, (
            f"{app.product_type_name}: term {appr.term_months} not "
            f"in {spec.term_months}"
        )


def test_balance_ordering(
    profile: SynthProfile,
    catalog: ProductCatalog,
    members: list[MemberRow],
) -> None:
    origence = generate_origence_data(profile, catalog, members)
    symitar = generate_symitar_data(origence, profile, catalog)
    amounts: dict[str, list[float]] = {
        "first_mortgage": [], "auto_indirect": [], "credit_card": [],
    }
    for loan in symitar.booked_loans:
        if loan.product_type_name in amounts:
            amounts[loan.product_type_name].append(float(loan.original_balance))
    mtg_mean = sum(amounts["first_mortgage"]) / len(amounts["first_mortgage"])
    auto_mean = sum(amounts["auto_indirect"]) / len(amounts["auto_indirect"])
    card_mean = sum(amounts["credit_card"]) / len(amounts["credit_card"])
    assert mtg_mean > auto_mean, (
        f"first_mortgage mean {mtg_mean:.0f} not > auto_indirect mean {auto_mean:.0f}"
    )
    assert auto_mean > card_mean, (
        f"auto_indirect mean {auto_mean:.0f} not > credit_card mean {card_mean:.0f}"
    )


def test_auto_indirect_has_dealer_after_attach(
    profile: SynthProfile,
    catalog: ProductCatalog,
    members: list[MemberRow],
) -> None:
    from synth_data.generators.dealers import generate_dealers
    dealers = generate_dealers(profile)
    origence = generate_origence_data(profile, catalog, members)
    symitar = generate_symitar_data(origence, profile, catalog, dealers=dealers)
    indirects = [
        loan for loan in symitar.booked_loans
        if loan.product_type_name == "auto_indirect"
    ]
    assert indirects, "expected at least one auto_indirect loan"
    assert all(loan.dealer_id is not None for loan in indirects), (
        "every auto_indirect loan must have dealer_id set after attach"
    )
    # No other product should have a dealer_id.
    for loan in symitar.booked_loans:
        if loan.product_type_name != "auto_indirect":
            assert loan.dealer_id is None, (
                f"non-indirect loan {loan.loan_id} ({loan.product_type_name}) "
                f"has dealer_id={loan.dealer_id}"
            )
