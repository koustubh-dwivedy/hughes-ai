# ADR-0009 — No new mf_query cache yet (validate-then-act)

**Date:** 2026-05-16
**Issue:** HUG-249
**Status:** Accepted (measurement phase)

## Context

The autonomous lead agent (HUG-244) dispatches multiple subagents per
deep-research turn (HUG-243). Each subagent calls `mf_query` against
MetricFlow. There was concern (planning conversation, 2026-05-16) that
overlapping queries across subagents would re-execute the same
MetricFlow subprocess invocations and slow turns substantially.

A prior proposal (HUG-249's original scope) was to add a new
turn-scoped LRU cache module for `mf_query` results. After validation
that:

1. The chat agent already benefits from `@lru_cache(maxsize=1)` on
   `list_metrics()` at `packages/nl-engine/src/nl_engine/repo/metricflow.py:132`,
   which saves ~96 min per 24-question must-pass eval (per the
   cache's own docstring);
2. A backend response cache exists at
   `packages/api/src/api/service/dashboard_query.py:35-82` covering
   `/dashboards/*` endpoints (5-min TTL, in-process dict, Prometheus
   counter);
3. The lead agent's tool registry is exactly the same as the chat
   agent's for `list_metrics` / `lookup_metric_definition` — both go
   through `safe_mf().list_metrics()` and hit the existing lru_cache;

…the right move was reframed from "add new cache module" to "measure
first; add cache extension only if latency budget breached."

## Decision

**Phase 1 — measurement, no new cache.**

- The deep-research eval harness (HUG-248) captures per-question
  `elapsed_s` in the artefact returned by `_run_one_question`.
- `mf_query_runner.py:_log_mf_run` (already in place) emits a
  `mf_query.run` structlog event per call with metric name, args hash,
  and elapsed-ms. The harness can aggregate these post-run from the
  captured event stream.
- After running the 14-question suite via `make deep-eval`, compute:
  median + p95 turn latency, median + p95 mf_query latency, count of
  duplicate `(metric, dims, where)` invocations within each turn.

**Decision gate.** If all three of:

1. median deep-research turn ≤ **8s** (with cached `list_metrics()`)
2. p95 deep-research turn ≤ **20s**
3. duplicate-query rate < **20%** across the 14-question batch

…hold, we DO NOT add a new cache. The existing cache shape suffices.

If any threshold is breached, file a follow-up (HUG-250) to extend
the **existing `dashboard_query.py` pattern** (in-process dict + 5-min
TTL + Prometheus counter) to `mf_query`. Specifically NOT a new cache
module — we extend what's there. Estimated ~30 LOC of new code.

## Why this matters

The earlier HUG-249 plan proposed a 200-LOC new cache module before
any measurement existed. The user (correctly) pushed back: "look into
that and not directly jump on adding yet another slop in the codebase
before complete validation." This ADR records the validate-first
discipline so future contributors don't re-litigate.

## Consequences

- **HUG-249 ships doc-only.** No code change, no NL Eval trigger.
- **HUG-250 conditional.** Filed only if measurement breaches the
  gate. Until then, nothing to do.
- **mf_query latency captured today** via existing structlog events;
  no new instrumentation required. The deep_eval harness already
  records turn-level `elapsed_s` per question.

## Verification

Run `make deep-eval` once `RESEARCH_LEAD_AGENT_ENABLED=1` against a
local Postgres + Ollama Cloud. The harness prints median + p95 turn
latency at the bottom of its report. Compare against the thresholds
above; record the result on this ADR (amendment block below) and act
accordingly.

## Amendments

_None yet — pending the first real run._
