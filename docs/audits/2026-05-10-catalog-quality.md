# Catalog Quality Audit — 2026-05-10

## Scope
Absolute audit of `packages/dbt-models/models/semantic/`. Not eval-linked. Each
finding evaluates the catalog on its own merits — coverage gaps a CU analyst
would notice, reference integrity, naming/type consistency, description
quality, orphan detection, and time-grain coverage.

Files audited (full read):
`applications.yml`, `cecl.yml`, `delinquency.yml`, `deposits.yml`, `dims.yml`,
`executive_kpis.yml`, `lifecycle.yml`, `loans.yml`, `metrics.yml`,
`metricflow_time_spine.yml`. Underlying marts (`fct_loans_monthly.sql`,
`fct_delinquency_monthly.sql`, `fct_deposits_monthly.sql`,
`fct_loan_lifecycle_events.sql`) cross-checked to verify which physical
columns actually back each dimension/measure.

## Summary
- 18 findings: 5 high, 7 medium, 6 low

## Findings

### F-001 — `delinquency_rate` cannot slice by `product_type`
- **File**: `packages/dbt-models/models/semantic/delinquency.yml:1-35` (and underlying mart `packages/dbt-models/models/marts/fct_delinquency_monthly.sql:1-48`)
- **Severity**: high
- **Axis**: domain coverage gap, reference integrity (numerator/denominator dimension mismatch)
- **Description**: The `delinquency_monthly` semantic model exposes only
  `as_of_month`, `delinquency_bucket`, `officer`, and `branch`. There is no
  `product_type` dimension on the numerator side. The denominator
  (`total_loans` on `loans_monthly`) does have `product_type`. As a result,
  `delinquency_rate` cannot be group-by'd on product_type — the metric is
  unusable for the most common CU analyst question ("delinquency rate by
  product"). Confirmed by reading `fct_delinquency_monthly.sql`: `product_type`
  is never carried through; the grain is
  `(as_of_month, officer_id, branch_id, bucket)` with no product key.
- **Proposed fix**: Add `product_type` to the SELECT/GROUP BY of
  `fct_delinquency_monthly.sql` (join through `booked_loans` → `product_types`
  exactly as `fct_loans_monthly.sql` already does). Then add
  `- name: product_type` (categorical) to the `delinquency_monthly` semantic
  model. Numerator and denominator will then share the slice key.
- **Effort**: ~1 hour (mart change + semantic model add + dbt rebuild + mart row-count test update)

### F-002 — `dealer_concentration_pct` has no usable dealer dimension on its measure
- **File**: `packages/dbt-models/models/semantic/metrics.yml:270-275`, cross-ref `loans.yml:7-42`
- **Severity**: high
- **Axis**: reference integrity
- **Description**: `dealer_concentration_pct` maps to measure
  `total_loan_balance`, which lives on `loans_monthly`. But `loans_monthly`
  has no `dealer` entity (entities are only `branch` and `officer`). Only the
  per-loan `dim_loan` semantic model carries `dealer`. So the metric's stated
  intent ("slice-by dealer_id on the loans semantic model") cannot be
  satisfied — there is no MetricFlow join path from `loans_monthly` to
  `dim_loan` (no shared entity), and `dim_loan` has no balance measure.
  Functionally, `dealer_concentration_pct` is broken.
- **Proposed fix**: Either (a) add a `dealer` foreign entity + dealer dim on
  `fct_loans_monthly` (requires carrying `dealer_id` through the mart), or
  (b) move the metric to a new per-loan measure on `loan_performance` and
  add `dealer` foreign entity there. Option (a) is preferred for portfolio-level
  rollups.
- **Effort**: ~1 hour

### F-003 — `household_balance` metric has no path from members→deposits
- **File**: `packages/dbt-models/models/semantic/metrics.yml:262-267`, cross-ref `dims.yml:91-108`, `deposits.yml:1-46`
- **Severity**: high
- **Axis**: reference integrity, orphan
- **Description**: `household_balance` is a `simple` metric on
  `total_deposit_balance` (`deposits_monthly`). But `deposits_monthly`'s
  entities are only `deposit_product` and `branch` — there is no `member` or
  `household` entity. The `households` semantic model in `dims.yml` declares
  a primary `household` entity but is never referenced as a foreign key
  anywhere else, so it cannot join to balances. The metric returns total
  deposits, NOT household balance. Either the metric is misnamed or the
  bridge `bridge_account_owner` / `bridge_household_member` (present in
  `core/`) needs to surface as semantic entities.
- **Proposed fix**: (a) Add `account` / `member` / `household` entities to
  `deposits_monthly` via the bridge tables, OR (b) remove the metric until
  the join graph supports it (preferred; documented as a known limitation).
- **Effort**: <30 min for option (b); ~half day for option (a)

### F-004 — `applications` / `fundings` lack `branch` and `officer` entities
- **File**: `packages/dbt-models/models/semantic/applications.yml:1-56`
- **Severity**: high
- **Axis**: domain coverage gap
- **Description**: A CU analyst expects to slice origination volume,
  approvals, and funded amount by branch and officer. Neither
  `applications` nor `fundings` exposes a `branch` or `officer` entity —
  applications has only `application` (primary) and `member` (foreign); the
  only categorical dims are `product_type`, `channel`, `status`. So
  `origination_volume by branch`, `funded_amount_total by officer`, and
  `approval_rate by branch` all fail. This is the second most common CU
  analyst dimension after time.
- **Proposed fix**: Carry `branch_id` (via `booked_loans` join, applied at
  application time when available) and `officer_id` through the staging
  layer for both `stg_origence_applications` and `stg_origence_fundings`,
  then add foreign entities on the semantic models.
- **Effort**: ~half day (touches stg models + semantic models + mart tests)

### F-005 — `loans_monthly` lacks `channel` dimension
- **File**: `packages/dbt-models/models/semantic/loans.yml:7-42`, cross-ref `loans.yml:78-111` (`dim_loan` has it)
- **Severity**: high
- **Axis**: domain coverage gap
- **Description**: `dim_loan` carries `channel` (direct vs indirect — a
  Origence vs Symitar split that is core to CU lending analysis). But the
  aggregate `loans_monthly` (where all balance-shaped metrics live —
  `total_loans`, `portfolio_balance`, `weighted_avg_loan_rate`, etc.) does
  not. There is no shared entity between `loans_monthly` (entities: branch,
  officer) and `dim_loan` (entity: loan, dealer), so `total_loans by
  channel` cannot be produced via MetricFlow. CU executives routinely ask
  "indirect vs direct portfolio share" — this is a first-order gap.
- **Proposed fix**: Add `channel` to the GROUP BY of `fct_loans_monthly.sql`
  (it is already available on `booked_loans`) and expose it as a categorical
  dimension on the semantic model.
- **Effort**: ~1 hour

### F-006 — Branch surfaces inconsistently across catalog
- **File**: `packages/dbt-models/models/semantic/dims.yml:56-67` (entity), `dims.yml:7-24` (members has `home_branch_name`/`home_branch_region` as raw cols), `loans.yml:78-111` (`dim_loan` has `branch_name`/`branch_region` as raw cols, no `branch` entity), `dims.yml:72-86` (`officers.officer_branch` is a raw col)
- **Severity**: medium
- **Axis**: internal consistency, naming
- **Description**: Branch is represented FOUR different ways:
  (1) `branches` primary entity + `branch_name`/`branch_region` dimensions
  (the canonical surface);
  (2) `members.home_branch_name` / `home_branch_region` raw columns;
  (3) `loans` (dim_loan) `branch_name` / `branch_region` raw columns with
  no `branch` foreign entity;
  (4) `officers.officer_branch` (expr: branch_name) raw column.
  An LLM reasoning across these will see three columns named `branch_name`
  and one named `home_branch_name` and have no canonical way to know they
  refer to the same entity. Joins via the `branch` entity are only available
  on `loans_monthly`, `deposits_monthly`, and `delinquency_monthly`.
- **Proposed fix**: Add a `branch` foreign entity (expr: `home_branch_id`)
  to `members`, and to `dim_loan` (`expr: branch_id`), and to `officers`
  (`expr: branch_id` if the column exists). Drop the redundant
  `branch_name`/`branch_region` dims from each non-canonical model. Members'
  `home_branch_*` can stay as separate dims if the "home" semantic is
  meaningful, but they should be derived through the `branch` join.
- **Effort**: ~1 hour

### F-007 — `status` is an overloaded dimension name across three models
- **File**: `applications.yml:25-26` (application status), `loans.yml:99-100` (loan status), `dims.yml:85-86` (officer status)
- **Severity**: medium
- **Axis**: internal consistency, naming
- **Description**: Three semantic models each declare a categorical dim
  called `status` with completely different value spaces (application
  pipeline state vs loan status vs officer employment status). MetricFlow
  resolves these via the semantic model qualifier, but for an LLM doing
  catalog reasoning the bare name `status` is dangerously ambiguous.
- **Proposed fix**: Rename to `application_status`, `loan_status`,
  `officer_status` (each with `expr: status` to keep the underlying column).
- **Effort**: <30 min

### F-008 — Catalog uses single-underscore dim names; spec calls for `<entity>__<column>`
- **File**: throughout (e.g. `dims.yml:64-67` `branch_name`, `branch_region`; `dims.yml:80-86` `officer_name`, `officer_branch`; `loans.yml:93-100` `branch_name`, `branch_region`)
- **Severity**: medium
- **Axis**: naming convention compliance
- **Description**: The stated convention is `<entity>__<column>` (double
  underscore). Catalog universally uses single underscore (`branch_name`,
  `officer_name`, `home_branch_region`, etc.). MetricFlow itself renders
  the qualified form in queries, but the source dim names do not follow
  the convention. Either the convention is wrong / aspirational, or a
  systematic rename is required.
- **Proposed fix**: Decide. Option A — accept current naming and remove the
  convention from CLAUDE/docs. Option B — bulk-rename source dims to
  `<entity>__<column>` (`branches.branch__name`, `branches.branch__region`)
  and update every metrics.yml + grounding-language reference. Option A is
  recommended because MetricFlow auto-qualifies on output.
- **Effort**: <30 min for option A; ~half day for option B

### F-009 — No `description:` field on any dimension or measure
- **File**: every file in `packages/dbt-models/models/semantic/`
- **Severity**: medium
- **Axis**: description quality
- **Description**: The `description:` key only appears at the
  `semantic_models[*].description` and `metrics[*].description` levels.
  No individual dimension or measure has a description. This is a
  significant LLM-usability gap: the agent sees `delinquency_bucket`
  (categorical) with no hint that values are like '30-59', '60-89', '90+'.
  Same for `bucket`, `event_type`, `dealer_type`, `markup_tier`,
  `is_core_deposit`, `cecl_segment_code`, etc. — each one needs a one-line
  description (and ideally an enumerated value list).
- **Proposed fix**: Add `description:` to every dim and measure across all
  10 yml files. Mechanical pass; ~50–60 fields total.
- **Effort**: ~1 hour

### F-010 — `watchlist_count` description is wrong
- **File**: `metrics.yml:225-230`, cross-ref `lifecycle.yml:1-30` and `fct_loan_lifecycle_events.sql:1-53`
- **Severity**: medium
- **Axis**: description quality, reference integrity
- **Description**: Description says "Count of loan-lifecycle 'renewed' or
  'paid_off' events as a watchlist proxy." But the lifecycle mart only
  emits `event_type IN ('new', 'paid_off')` — there is no `'renewed'`
  event. So the metric counts the union of new + paid_off events for the
  period (not filtered by event_type at all), which has no analytical
  relationship to a watchlist. An LLM grounding on this description will
  produce wrong answers.
- **Proposed fix**: Either (a) add a real watchlist surface (e.g. loans
  with DPD trending up over N months) and back the metric with that, or
  (b) remove the metric and rely on `delinquency_aging_distribution` for
  the watchlist concept. Until then, fix the description to reflect what
  the measure actually counts.
- **Effort**: <30 min for description fix; ~half day for real watchlist

### F-011 — `nonperforming_loan_balance` and `nonaccrual_balance` are silently identical to `delinquent_balance`
- **File**: `metrics.yml:203-216`
- **Severity**: medium
- **Axis**: description quality, internal consistency
- **Description**: All three metrics map to the same `delinquent_balance`
  measure on `delinquency_monthly`. Their descriptions claim distinct
  semantics ("90+ DPD", "synonym", etc.) but at the catalog level they
  return the same number for the same slice. Specifically,
  `nonaccrual_balance` claims to filter to 90+ DPD but does not — without a
  `delinquency_bucket` filter the metric returns ALL delinquent balance.
  An LLM will trust the description and produce wrong reports.
- **Proposed fix**: Define `nonaccrual_balance` as a `simple` metric on a
  new measure restricted to `delinquency_bucket = '90+'`, OR convert it to
  a derived metric with the bucket filter expressed as a constraint. Drop
  `nonperforming_loan_balance` (true synonym; pollutes catalog).
- **Effort**: ~1 hour

### F-012 — `portfolio_balance` is a duplicate of `total_loans` with no semantic difference
- **File**: `metrics.yml:73-78`
- **Severity**: low
- **Axis**: orphan / dead code (catalog clutter)
- **Description**: Comment says "Synonym for total_loans; kept for
  grounding-language familiarity." Two metric names map to the same
  measure with the same dimensions. If the grounding layer (DSPy modules)
  needs the synonym, document it via a `synonyms:` field in
  `context/metrics.yaml` rather than duplicating the metric. As-is, an LLM
  asked which to use has no signal.
- **Proposed fix**: Remove `portfolio_balance` from `metrics.yml`; add it
  as a synonym in `packages/nl-engine/context/metrics.yaml` (HUG-181
  grounding layer).
- **Effort**: <30 min

### F-013 — `funding_rate` and `approval_rate` are exact duplicates
- **File**: `metrics.yml:48-63`
- **Severity**: low
- **Axis**: orphan / dead code
- **Description**: Both are ratios of `funded_count / origination_volume`,
  with `funding_rate`'s description openly admitting "(same as approval
  rate under our synthetic data)". Either keep one and make the other a
  synonym, or differentiate one to count `status = 'approved'` (when that
  data is added).
- **Proposed fix**: Remove `funding_rate`, route synonyms through the
  grounding layer.
- **Effort**: <30 min

### F-014 — `is_core_deposit` is duplicated as a dim on two semantic models
- **File**: `deposits.yml:22-24` (deposits_monthly) and `deposits.yml:60-62` (deposit_products)
- **Severity**: low
- **Axis**: type consistency, internal consistency
- **Description**: Both are categorical with `expr: is_core_deposit::TEXT`.
  The mart already joins `dim_deposit_product` to populate the column, so
  the dim is reachable two ways: via the `deposit_product` entity join, or
  directly on the fact. If the dim definition on `dim_deposit_product`
  changes (e.g. capitalization of values), the fact-side dim will silently
  disagree.
- **Proposed fix**: Drop the dim from `deposits_monthly`; require the
  `deposit_product` join to access `is_core_deposit`. Or vice versa.
- **Effort**: <30 min

### F-015 — `executive_kpis` measures use `agg: max` for ratios — fragile if grain changes
- **File**: `executive_kpis.yml:18-49`
- **Severity**: low
- **Axis**: type consistency
- **Description**: All ratio measures (`loan_to_deposit_ratio`,
  `core_deposit_ratio`, `blended_past_due_ratio`, `rate_spread`, etc.) use
  `agg: max`. Works only because the mart guarantees one row per month. If
  the grain is ever extended (per-branch executive KPIs, for instance),
  `max` will produce silently-wrong cross-month aggregations.
- **Proposed fix**: Either (a) document the one-row-per-month invariant in
  the semantic model description and add a structural test, or (b) change
  to `agg: average` for ratios so cross-month rollup is at least
  arithmetically defensible.
- **Effort**: <30 min

### F-016 — `members` semantic model is reachable but has no metric using it
- **File**: `dims.yml:7-24`
- **Severity**: low
- **Axis**: orphan
- **Description**: `members` declares a primary `member` entity and four
  dims (`full_name`, `home_branch_name`, `home_branch_region`,
  `joined_at`). The `member` entity is referenced as a foreign key on
  `applications` only. No metric in `metrics.yml` is sliceable by member,
  and neither `loans_monthly` nor `deposits_monthly` carries a `member`
  entity. The model is a join-island.
- **Proposed fix**: Either add `member` foreign entity to `loans_monthly`
  and `deposits_monthly` (so `top_n_borrowers` and `top_n_deposits` can
  resolve member names), or shrink the `members` model and document why.
- **Effort**: ~1 hour

### F-017 — `households` semantic model is fully orphaned
- **File**: `dims.yml:91-108`
- **Severity**: low
- **Axis**: orphan
- **Description**: `households` defines a primary `household` entity but
  no other semantic model declares `household` as a foreign entity. Cannot
  participate in any join. See also F-003 — the only metric that
  conceptually uses households (`household_balance`) routes around it.
- **Proposed fix**: Either delete `households` from `dims.yml` (until a
  bridge entity is added) or wire `household` foreign entity into
  `deposits_monthly` via `bridge_account_owner` + `bridge_household_member`.
- **Effort**: <30 min for delete; ~1 hour to wire properly

### F-018 — `cecl_allowance` only exposes month grain; no day/quarter/year
- **File**: `cecl.yml:1-37`
- **Severity**: low
- **Axis**: time-grain consistency
- **Description**: `cecl_allowance.period_end_month` is declared with
  `time_granularity: month` only. Other monthly facts also declare month
  only and rely on MetricFlow auto-rollup, which does support quarter and
  year. So this is consistent with the rest of the catalog. Flagging as
  low so it surfaces alongside any future grain-coverage policy decision —
  if quarter/year are required to be explicit (per the audit prompt's
  axis 4), every `month`-grain semantic model needs the same upgrade.
- **Proposed fix**: Confirm policy. If implicit rollup is acceptable,
  document it; if explicit grains are required, add `quarter` and `year`
  granularity declarations consistently across all monthly facts.
- **Effort**: <30 min for documentation; ~1 hour for explicit grains

## Applied in this plan (commit accompanying this audit)

- **F-001 (FIXED)** — Added `product_type` to `fct_delinquency_monthly`
  via the `booked_loans → product_types` join; introduced
  `dim_product_type` core model + `product_types` semantic model holding
  `product_type` as a primary entity; converted `product_type` from a
  bare categorical dimension to a foreign entity on `loans_monthly`,
  `delinquency_monthly`, `applications`, `loan_lifecycle_events`, and
  `loans` (dim_loan) so the slice key resolves consistently across
  ratio metrics. Verified: `delinquency_rate × product_type` now returns
  5 rows; `total_loans × product_type` (Q21) preserved.

## Deferred (out of scope for this plan)

The audit's "recommended for this plan" list was scoped down to the
single eval-blocking item (F-001) once the second high-severity item
(F-005, channel on `loans_monthly`) turned out to require an
upstream-staging change that exceeded the 2-hour budget rule. The
remaining "recommended" items (F-007 status rename, F-009 add
descriptions everywhere, F-010 watchlist_count description fix) are
medium-severity and are filed for follow-up. Originally:


- **F-001** — `delinquency_rate` × `product_type` is the explicit Q14 eval
  blocker called out in the audit prompt. Fix is local: add `product_type`
  to `fct_delinquency_monthly.sql` (already trivially joinable via
  `booked_loans` → `product_types`) and expose the dim. ~1 hour.
- **F-005** — Adding `channel` to `loans_monthly` is the same shape as
  F-001 and unblocks first-order CU executive questions ("indirect vs
  direct portfolio share"). ~1 hour.
- **F-007** — `status` rename to `application_status` / `loan_status` /
  `officer_status` is a 30-minute mechanical change that materially
  improves agent disambiguation.
- **F-009** — Add `description:` to every dim and measure. Mechanical,
  ~1 hour, and is the highest leverage change for LLM grounding quality.
- **F-010** — Fix the `watchlist_count` description (it currently misleads
  the LLM about what the metric counts). <30 min.

## Defer to follow-up ticket:
- **F-002** (dealer concentration) — high severity but requires mart-shape
  change and a new entity; cleaner as its own ticket.
- **F-003** / **F-016** / **F-017** (member/household join graph) — touches
  bridge tables and stg layer; not a single-sitting change.
- **F-004** (branch/officer on applications + fundings) — requires
  staging-layer changes upstream of this catalog; ~half day.
- **F-006** (canonical branch entity everywhere) — coordinated rename
  across multiple models + metrics.yml; cleaner as a follow-up.
- **F-008** (naming convention) — needs a policy decision before any
  rename; not blocking.
- **F-011** (nonaccrual semantics) — needs new measure + bucket filter
  design; cleaner as its own ticket.
- **F-012** / **F-013** (synonym dedup) — properly belongs in the grounding
  layer (HUG-181), not the semantic catalog.
- **F-014** (`is_core_deposit` dedup) — cosmetic.
- **F-015** (`agg: max` on exec_kpis) — cosmetic until grain changes.
- **F-018** (explicit time grains on cecl) — pending policy decision.
