# ADR-0001: Dashboard Fetch Strategy

**Date:** 2026-04-30
**Status:** Accepted

---

## Context

Hughes AI ships four pre-built dashboard views (Executive Summary, Deposit Portfolio,
Past Due, Officer/Branch Loans) alongside the existing open-ended NL chat. We needed
to decide how the frontend fetches dashboard data and how several cross-cutting concerns
are handled: data freshness, temporal filtering, trust panel scope, and synthetic-data
disclosure.

---

## Decisions

### 1. Dedicated mart-backed endpoints, not LLM-routed queries

Each dashboard calls its own typed API endpoint (`/api/dashboards/<name>`) backed by
a specific dbt mart. The NL `/ask` pipeline is **not** used for dashboard data.

**Why:** Dashboard KPIs must be deterministic, fast, and schema-stable. The LLM pipeline
adds latency (2–30 s), non-determinism, and hallucination risk that are acceptable for
exploratory chat but unacceptable for a scoreboard a CLO glances at each morning.
Mart-backed queries run in < 200 ms and return typed responses validated by Pydantic.

### 2. Cache TTL: 5 minutes (client-side)

`DashboardEnvelope` includes `generated_at` (ISO timestamp). The frontend re-fetches on
component mount; a client-side cache keyed on `(endpoint, as_of_date)` with a 5-minute
TTL prevents redundant refetches within a single session.

**Why:** Dashboard data is backed by daily snapshots — re-fetching more often than once
every 5 minutes provides no new information and wastes DB reads.

### 3. `as_of_date` URL parameter for temporal filtering

All dashboard endpoints accept `?as_of_date=YYYY-MM-DD`. The frontend reads this from
the URL search param via `DashboardContext`, threads it through `useDashboard`, and
appends it to the query string. Omitting it defaults to the latest available snapshot.

**Why:** Demos and QA need to pin to a specific date without changing seeded data.
URL-param approach keeps the date shareable (copy-paste URL) and avoids hidden state.

### 4. Loans-only reconciliation invariant on the Trust panel

`/api/trust` continues to report Origence↔Symitar reconciliation for **loans only**,
even though the Deposit Portfolio dashboard now ships deposit data. Deposit reconciliation
(core deposits vs. a deposit origination system) is out of scope for v1.

**Why:** Widening the reconciliation scope would require a second source-of-truth system
for deposits (none exists in the current synthetic data pipeline). Shipping a partial
reconciliation metric would give a false sense of deposit data integrity. The trust
panel explicitly labels its scope as "loans" to make this boundary visible.

### 5. Demo-data banner for PII-shaped panels

The Officer/Branch Loans dashboard surfaces a top-25 borrower table with synthetic
member names (e.g. "Member 1"). A persistent `role="note"` banner reading
*"Demo data only — borrower names are synthetic and do not represent real members."*
is rendered at the top of the panel on every load.

**Why:** Synthetic names are intentionally realistic-looking to make the demo credible.
Without a visible disclosure, a viewer could mistake them for real member data. The
banner is non-dismissible and renders unconditionally — it cannot be hidden by a
loading or error state.

---

## Consequences

- Dashboard endpoints are owned by `packages/api/src/api/routes/dashboards/` and tested
  independently from the NL pipeline.
- Adding a new dashboard requires: a dbt mart, a Pydantic response type, a FastAPI route,
  a React dashboard module under `src/dashboards/`, a route entry in `src/router.tsx`, a
  nav item in `src/layout/SideNav.tsx`, and a Playwright spec in `tests/e2e/`.
- The Trust panel scope (loans only) is documented in `docs/metrics.md` and must be
  explicitly widened in a future ADR if deposit reconciliation is added.
