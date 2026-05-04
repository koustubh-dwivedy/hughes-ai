# ADR-0002: Synthetic Data Model Revamp (CU-Realistic Grounding)

**Date:** 2026-05-04
**Status:** Accepted

---

## Context

The original Hughes AI synthetic model was built on intuition and showed it: a generic
`Consumer` loan bucket, a `PPP` product that dates the data to 2020, three commercial
buckets (`CRE` / `C&I` / `Construction`) that real CUs file as a single Member Business
Loan line on the NCUA 5300, no concept of household or joint ownership, no dealer
entity behind indirect auto lending (Origence's flagship workflow), no NCUA call-report
mapping, and no CECL allowance roll-forward.

We evaluated **Microsoft's Industry-Accelerator-FinancialServices**
(<https://github.com/microsoft/Industry-Accelerator-FinancialServices/>) as a possible
schema reference.

## Decision

We **adopt the Microsoft model only as a vocabulary checklist** for Customer-360,
Household, Joint-ownership, and Loan-onboarding concepts. We do **not** restructure
our marts around its `FinancialHolding` abstraction, and we do **not** take any
runtime dependency on it.

Reasons:
1. **Archived July 2024** (last release Sep 2022). Not a maintained foundation.
2. **CRM-shaped, not analytics-shaped.** It is a Dynamics 365 / Dataverse solution
   for bank sales/service teams. It has no transaction ledgers, no delinquency
   bucket structure, no dual-system reconciliation pattern, no dealer/indirect
   lending entity, no NCUA semantics — all of which we already have.
3. **Adopting `FinancialHolding` would force a SQL refactor for net-zero analytical
   gain.** Our `fct_loans_monthly` / `fct_deposits_monthly` shape is already
   purpose-built for the questions our dashboards and NL chat ask.

We therefore borrow only the *concepts* it surfaces well — `Group` (household),
`GroupMember`, `Relationship`, joint ownership of `FinancialHolding` instruments —
and reimplement them as first-class entities native to our analytical schema.

## Scope of the revamp

In scope:
- New 6-product loan taxonomy (Auto-Direct, Auto-Indirect, First Mortgage, HELOC,
  Closed-End 2nd Lien, Credit Card). Drops PPP, Consumer, CRE, C&I, Construction.
- Dealer entity + `dealer_id` FK on Auto-Indirect bookings (Origence's flagship).
- Household + joint-owner + POD-beneficiary modeling.
- Full NCUA 5300 line-item catalog and `fct_call_report` mart.
- CECL allowance roll-forward (`fct_cecl_allowance_rollforward`).
- Credit-card transaction ledger.
- Audit harness (`make audit`) gating cross-system reconciliation, logical
  invariants, statistical sanity, regulatory closure, and grounding consistency.

Out of scope (deferred):
- Onboarding-depth entities (Collateral with VIN, CreditCheck/FICO history,
  Employment, KYC, Documents).
- New share products (IRA, HSA, Club).
- New dashboards for the new domains — the existing four stay shape-compatible
  and a follow-up plan adds Member 360 / Regulatory / Indirect Lending / Card.

## Consequences

- Existing dashboards keep rendering; their *values* shift because the underlying
  data is regenerated with the new product mix. CHANGELOG entry called out.
- Anyone with example queries against `Consumer` or `PPP` gets zero rows; the NL
  `examples.yaml` is swept to remove these references.
- The CECL implementation is a simplified expected-loss model (DPD-band loss rates
  × balance), not a true CECL methodology. Documented in `docs/metrics.md` so we
  don't oversell.
- Microsoft accelerator will be re-evaluated only if Microsoft revives it or we
  spec a CRM-shaped product surface, which we don't have on the roadmap.
