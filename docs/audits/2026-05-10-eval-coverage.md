# Eval-vs-Catalog Coverage Matrix — 2026-05-10

## Scope
Cross-check between the must-pass eval set and the MetricFlow catalog
(post Step 3 fixes). Two questions:

1. Can every must-pass question's `expected_metric × expected_dimensions`
   be answered by the catalog?
2. Are there major catalog capabilities that NO must-pass question
   exercises?

This is a downstream check from the absolute catalog audit
(`2026-05-10-catalog-quality.md`); it tests COVERAGE in both
directions, not catalog quality on its own merits.

## Eval → Catalog (24 must-pass questions)

| ID  | Metric                  | Dimensions          | Catalog supports? |
|-----|-------------------------|---------------------|-------------------|
| 001 | loan_to_deposit_ratio   | —                   | ✅                 |
| 002 | total_loans             | —                   | ✅                 |
| 003 | total_deposits          | —                   | ✅                 |
| 004 | rate_spread             | —                   | ✅                 |
| 005 | past_due_ratio          | —                   | ✅                 |
| 006 | deposits_by_product     | deposit_product     | ✅                 |
| 007 | deposits_by_branch      | branch              | ✅                 |
| 008 | mtd_deposit_change      | —                   | ✅                 |
| 009 | deposits_by_product     | is_core_deposit     | ✅                 |
| 010 | origination_volume      | —                   | ✅                 |
| 011 | origination_volume      | channel             | ✅                 |
| 012 | origination_volume      | product_type        | ✅                 |
| 013 | avg_loan_amount         | —                   | ✅                 |
| 014 | delinquency_rate        | product_type        | ✅ (Step 3 F-001)  |
| 015 | past_due_loan_count     | —                   | ✅                 |
| 016 | past_due_ratio          | as_of_month         | ✅                 |
| 017 | watchlist_count         | —                   | ✅ (semantically wrong; F-010) |
| 018 | nonaccrual_balance      | —                   | ⚠️ (returns all delinquent balance, not 90+; F-011) |
| 019 | origination_volume      | channel             | ✅                 |
| 020 | total_loans             | branch              | ✅                 |
| 021 | total_loans             | product_type        | ✅                 |
| 022 | total_loans             | branch_region       | ✅                 |
| 023 | origination_volume      | event_type          | ✅ (lifecycle path) |
| 024 | (clarification — n/a)   | —                   | n/a               |

23/23 answerable, +1 clarification. Caveat: Q17 and Q18 return
plausible-looking numbers but for the wrong underlying definition (the
catalog's `watchlist_count` and `nonaccrual_balance` definitions are
known issues — see catalog audit F-010 / F-011). The numbers happen to
match the GTs because the GTs were derived from the same broken
definitions; this is a coverage issue masked by GT alignment.

## Catalog → Eval (capabilities not exercised by must-pass)

The catalog exposes these meaningful surfaces with NO must-pass
question hitting them:

- **`*_by_*` time-series rollups** (`metric_time__month`) — only Q016
  exercises a time-grain breakdown. Time-series is the most common
  CU executive ask but the must-pass barely touches it.
- **`branch_region`** — Q022 hits this once. No multi-region comparison
  question.
- **`officer_*` slicing** — every officer-grain metric is reachable but
  no must-pass slices by officer. Officer performance is a routine CU
  question type.
- **`cecl_*` metrics** (`cecl_allowance_balance`, `cecl_provision_ytd`)
  — reachable but never exercised. CECL reporting is regulator-driven.
- **`nonperforming_loan_balance`** — reachable but never exercised
  (also a duplicate of `delinquent_balance`; see catalog audit F-011).
- **`weighted_avg_loan_rate`, `weighted_avg_deposit_rate`** — rate
  metrics never exercised.
- **`top_n_borrowers`, `top_n_deposits`** — top-N queries never
  exercised by must-pass (long-tail covers them).
- **`single_loan_customers`** — never exercised.
- **`monthly_growth_*`** — month-over-month deltas never exercised.
- **`dealer_concentration_pct`** — never exercised (also currently
  broken per catalog audit F-002).
- **`household_balance`** — never exercised (also currently broken per
  catalog audit F-003).

## Recommendations (for follow-up ticket, not this plan)

The eval has a strong "headline KPI by one slice" bias. Future
must-pass expansions should add:

1. At least one time-series question per metric family
   (`metric_time__month`).
2. One officer-performance question (slice a metric by officer).
3. One CECL question.
4. One rate-spread or weighted-rate question (the things execs
   actually look at on rate-environment dashboards).

Catalog metrics flagged as broken by the catalog audit (F-002, F-003,
F-010, F-011) should either be fixed or removed BEFORE adding eval
coverage for them.
