# ADR-0007: Catalog and eval-quality are audited absolutely, not only relative to each other

**Date:** 2026-05-10
**Status:** Accepted
**Linear epic:** HUG-172
**Companion:** ADR-0006 (tool docstrings as prompts)

---

## Context

The 2026-05-10 forensic into the must-pass eval regression
(20/24 → 10/24) surfaced two systemic issues alongside the dominant
docstring-trim cause (ADR-0006):

1. **Catalog quality gap.** The MetricFlow semantic layer didn't
   expose every (metric × dimension) combination the must-pass
   questions demand. The most blatant example: `delinquency_rate`
   numerator (`delinquent_balance` on `delinquency_monthly`) and
   denominator (`total_loans` on `loans_monthly`) had no shared
   `product_type` entity, so "delinquency rate by product type"
   (must-pass-014) had no path through MetricFlow at all. Other
   metrics had broken descriptions (`watchlist_count` claimed to
   count something different than what its measure produces),
   functionally broken metrics with no usable join graph
   (`dealer_concentration_pct`, `household_balance`), and
   inconsistent naming across semantic models.

2. **Eval-quality issues.** Forensic preliminary read suggested
   ambiguous wording in must-pass-023 ("Show loan lifecycle event
   counts (new / renewed / paid_off)..."). On audit it turned out
   the GT was actually correct for the data — but the audit
   exposed that no one had been doing this kind of "is the wording
   defensible against the GT" review systematically.

A separate observation: the catalog was richer than the must-pass
eval probed. CECL metrics, weighted rate metrics, monthly growth
deltas, top-N queries, and officer slicing were all reachable but
unexercised by must-pass. The eval tier had a strong "headline KPI
by one slice" bias.

The catalog and the eval are two separate artifacts. Treating "does
the eval cover the catalog" as a substitute for "is the catalog any
good" or "is the eval any good" had been letting bugs accumulate in
both.

## Decision

This ADR formalizes three separate audit disciplines.

### 1. The catalog is audited on its OWN merits, not relative to the eval

An "absolute catalog audit" examines `packages/dbt-models/models/semantic/`
along these axes:

- **Internal consistency** — the same logical entity is named
  consistently across metrics (e.g. branch should always surface as
  `branch__branch_name`).
- **Naming convention compliance** — dimensions follow the
  `<entity>__<column>` shape. Deviations are flagged.
- **Domain-expert coverage gaps** — for each metric, does its
  dimension set match what a CU analyst would expect? E.g.
  `delinquency_rate` should slice by product_type and branch;
  `portfolio_balance` should slice by region and channel.
- **Time-grain consistency** — every time-series metric exposes
  the same `metric_time__*` grains.
- **Description quality** — every metric and dimension has a
  meaningful, LLM-usable `description` field.
- **Orphans and dead code** — semantic models, measures, or
  dimensions defined but never referenced.
- **Reference integrity** — every entity referenced exists; every
  join target exists; no broken refs.
- **Type consistency** — same logical dimension has the same type
  (categorical / time / numeric) across metrics.

Whether the must-pass eval ever exercises these is irrelevant to
this audit. A catalog can be passing the eval and still have rotten
internals.

The audit deliverable is a markdown report under
`docs/audits/YYYY-MM-DD-catalog-quality.md`, with each finding
captured as `{file:line | severity | description | proposed fix |
effort}`. The 2026-05-10 audit is the first instance and serves as
the template.

### 2. The eval is audited on its OWN merits, not relative to the catalog

An "eval-quality audit" reviews each question for:

- **Single defensible interpretation.** A question must read one
  way. If wording invites multiple readings, the wording is the bug
  — not the GT.
- **GT correctness for that interpretation.** Ground-truth rows
  match the natural reading of the question, not just one chosen
  reading among many.
- **GT correctness against the data.** The numbers in
  `ground_truth_rows` are what the data actually produces (verified
  by re-running the GT SQL).

When wording is ambiguous, **fix the wording**, don't hard-code one
reading in the GT. We do not lower the bar by making the eval
easier; we fix bugs in the questions or in the agent or in the
catalog.

The audit deliverable is a markdown report under
`docs/audits/YYYY-MM-DD-eval-quality.md`. The 2026-05-10 instance
is the first.

### 3. Eval-vs-catalog COVERAGE is a separate, third audit

Once 1 and 2 are clean, a coverage matrix runs in BOTH directions:

- **Eval → catalog**: every must-pass question's
  `expected_metric × expected_dimensions` is answerable by the
  catalog (no `mf_unsupported` failures).
- **Catalog → eval**: every meaningful catalog capability is
  exercised by at least one must-pass or long-tail question. Dead
  surfaces are surfaced as either eval gaps to close or catalog
  surfaces to remove.

Captured as `docs/audits/YYYY-MM-DD-eval-coverage.md`.

### 4. Adding a question to must-pass requires a coverage check

Before promoting a question to must-pass:

- Verify the catalog can answer it (run the GT SQL through MF, or
  confirm the equivalent metric path).
- Verify the wording has one interpretation.
- Verify the GT rows match what the data actually returns.

This blocks the easy regression where someone adds an aspirational
question that the catalog can't yet answer, then the eval fails
forever afterward.

## Consequences

### Positive

- Catalog rot is detected before it causes eval regressions.
- Eval rot is detected before it causes false negatives or false
  positives.
- The audit reports are durable artifacts with file:line
  references, so a future contributor can pick up an audit's
  deferred findings as a real follow-up ticket.

### Negative

- More artifacts to maintain. An audit that's never re-run is just
  a snapshot.
- Distinguishing "catalog audit" from "eval coverage" is real
  cognitive work — a contributor unfamiliar with the distinction
  will be tempted to conflate them. The 2026-05-10 instance
  documents the distinction explicitly to teach the pattern.

### Cadence

- Run the absolute catalog audit at every major catalog change
  (new metric, new semantic model, new entity), and at minimum
  once per quarter.
- Run the eval-quality audit before every must-pass expansion,
  and at minimum once per quarter.
- Run the coverage matrix after either of the above.

## Applied in this plan (2026-05-10)

- Absolute catalog audit produced 18 findings (5 high, 7 med, 6 low).
  The high-severity eval-blocking item (F-001: `delinquency_rate ×
  product_type`) was fixed in this plan; one other high-severity
  item (F-005: `channel` on `loans_monthly`) was scoped down after
  it turned out to require an upstream-staging change exceeding the
  2-hour rule. The remaining 16 findings are deferred to a
  follow-up ticket with the audit report as the spec.
- Eval-quality audit produced zero fixes — the forensic's
  preliminary calls on Q23 and Q8 were overruled by the audit
  (both turned out defensible after re-checking the data).
- Coverage matrix documented eval bias toward "headline KPI ×
  one slice"; recommendations recorded for follow-up.

## Amendment 2026-05-10b — first audit under-graded LLM-grounding ambiguity

The 2026-05-10 catalog audit was conducted along eight axes (internal
consistency, naming, domain coverage, time-grain, description quality,
orphans, reference integrity, type consistency). On re-review through
an LLM-grounding lens we found that **duplicate / synonym metrics**
(F-012 `portfolio_balance` ≡ `total_loans`, F-013 `funding_rate` ≡
`approval_rate`, F-011 `nonaccrual_balance` claiming 90+ but actually
returning all delinquent balance, plus F-019..F-024 misleadingly-named
near-synonyms) had been graded "low" because they were redundant
rather than broken. From the catalog's perspective, dead-code clutter
is low-severity. From an LLM agent's perspective with no synonym
table, two metrics returning the same number with different
descriptions is **actively harmful** — it forces the agent to either
guess or call `clarify`, and at temperature > 0 it picks differently
across runs.

This incident manifested in the 2026-05-10 must-pass eval as
hallucination-class failures: the agent picked `funded_count` over
`origination_volume` (Q10), `top_n_borrowers` over `origination_volume`
(Q12), and called `clarify` on `delinquency_rate` (Q14) because
`mf list dimensions` does not enumerate foreign entities and the
agent never saw `product_type` as a slice option.

This amendment adds a ninth audit axis:

> **9. LLM disambiguation quality.** For every pair of metrics that
> share a backing measure or whose names are semantically near, can
> an LLM with only `list_metrics()` output (name + description +
> dimensions) confidently pick the right one? If not, either rename,
> redescribe, or merge. Synonym tables are NOT a substitute — they
> may never ship. The catalog must be self-disambiguating.

The catalog overhaul committed alongside this amendment is the
corrective: catalog shrunk from 38 → 32 distinct metrics; every
duplicate either deleted or renamed; every description rewritten with
explicit "distinct from <sibling>" callouts; foreign entities
exposed via the agent's `list_metrics()` so dimension surfaces match
what the agent actually queries.

Status: Accepted (amendment).

## References

- `docs/audits/2026-05-10-catalog-quality.md` — first absolute
  catalog audit.
- `docs/audits/2026-05-10-eval-quality.md` — first eval-quality
  audit.
- `docs/audits/2026-05-10-eval-coverage.md` — first coverage
  matrix.
- ADR-0006 — companion ADR on tool docstrings as prompts.
