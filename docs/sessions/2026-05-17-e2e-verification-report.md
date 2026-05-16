# End-to-end product verification report (2026-05-17)

User asked for comprehensive end-to-end verification of the product
after the autonomous run shipped 13 issues. This is the consolidated
report with a decision matrix for every test.

## Headline

The autonomous run delivered a working backend lead-agent stack with
some sharp edges. Out of all tests run:

| Finding type | Count | Examples |
|---|---|---|
| ✓ Pass | ~40 | Backend routes, dashboards render, lead-agent end-to-end flow, ANCHOR-F discipline holding |
| ✗ **Regression** (I introduced) | **3** | PlanStatus literal missing 'proposed' (P0); write_memory FK violation (P0); HUG-245 deferred frontend regressions (P1) |
| ⚠ Pre-existing | 1 | `GET /threads/{tid}` ownership check missing (P0 security, predates autonomous run by 11 days) |
| 🔧 Expected-broken | 1 | PlanPreview's Approve button — documented in decommission audit |
| ⊘ Env-specific | 1 | `mf` binary PATH conflict with TeXLive's METAFONT (local only) |

**Phase B's CI + NL Eval both went green** — the decommission did not regress chat-agent accuracy. Lead-agent path tested end-to-end with real LLM: simple questions stay simple (3 tools), deep questions correctly trigger propose_plan + run_subagent + memory tools. **But two of the lead-agent's tools are silently broken** due to my own missed Pydantic+FK updates in HUG-241.

## Environment (Tier 0)

| Check | Result |
|---|---|
| Docker services (postgres, redis, vector, jaeger, victoria-metrics, victorialogs) | ✓ all up |
| Postgres data | ✓ 209 threads; subagent_calls + research_lead_notes + research_plans + threads + thread_messages all present |
| dbt semantic_manifest.json | ✓ present |
| `mf` binary (TeXLive shadows MetricFlow at PATH default) | ⊘ env-specific: prepend `$(pwd)/.venv/bin` to PATH; finds 32 metrics |
| API /health | ✓ 200 |
| Frontend Vite | ✓ 200 |
| Vector :8686/health | ✓ 200 |
| Victoria-Logs :9428 | ✓ 200 |
| Victoria-Metrics :8428 | ✓ 200 |
| Jaeger :16686 | ✓ 200 |
| LLM (Ollama Cloud glm-5.1) connectivity | ✓ 1.8s round-trip |
| Prometheus counter shapes (`hughes_*`) | ✓ all expected counters present |

## Backend route smoke (Tier 1, 24 tests)

22/24 pass. The 2 "fails":

- ✗ **`GET /threads/{tid}` wrong-user → 200 (expected 403). PRE-EXISTING BUG.** `routes/threads.py:208-221` has no ownership check. Function introduced 2026-05-05 (HUG-177), 11 days before this run. Even with NO auth headers, returns the thread. Same issue applies to `POST /threads/{tid}/messages` (no ownership check at line 224). **P0 security gap, not my regression but worth fixing soon.**
- ⊘ `/dashboards/available-months → 422` — endpoint requires `?surface=` query param; my test call shape was wrong. Not a real bug.

Every other route behaves correctly:
- ✓ `/health`, `/openapi.json`, `/metrics`, `/threads` POST + GET, plan GETs (latest, steps, findings, notes, subagent-calls), `/abort` (404 on missing plan), `/approve` 404 (route deleted in Phase B — works as designed), all 4 dashboards, `/trust`, `/history`, `/data-model/graph`.
- ✓ Wrong-user 403 confirmed on `/abort` route — `routes/research.py:_authorize_and_get_plan` DOES check ownership properly. The bug is specifically in `threads.py:get_thread`.

## Lead-agent flows (Tier 2)

### T2.1 — Simple chat question ✓ PERFECT

Question: "What is our total deposits in the latest month?"
- 3 tool calls: `list_metrics` → `mf_query` → `final_answer`
- Zero invocations of `propose_plan`, `run_subagent`, `read_memory`, `write_memory`
- **ANCHOR-F holding** — lead did NOT over-use heavy tools on a simple question
- Final answer: `"Our total deposits as of the latest month (May 2026) are $236,749,187.20."` — real data, real number.
- Thinking trace: 6 thinking + 6 step + 1 final events; persisted to `thread_messages` correctly.

### T2.2 — Deep multi-dimensional question ✓ EXCELLENT (with 1 regression revealed)

Question: "Decompose YoY past-due delta by branch and product. Which branches drove the increase? Use propose_plan to record your approach and run_subagent for each focused sub-question."

**SSE event summary:**
- `research.plan.drafted` × 1
- `research.subagent.spawned` × 3
- `research.subagent.completed` × 2
- `research.subagent.failed` × 1
- 21 thinking + 21 step events

**Tool call counts:**
| Tool | Calls |
|---|---|
| propose_plan | 2 (one replan!) |
| run_subagent | 5 |
| write_memory | 2 |
| list_metrics | 2 |
| mf_query | 9 |

**DB persistence:**
- 1 `research_plans` row (v1, status='proposed')
- 3 `subagent_calls` rows (2 complete with summaries + 1 failed)
- **0 `research_lead_notes` rows** ← **REGRESSION** (see Findings below)

The lead even gracefully recovered from a subagent failure. Final answer is real: "East Branch delinquency $1.59M, driven by first_mortgage" (truncated; the lead pivoted slightly because data doesn't actually support YoY for the synth-data history span, but the chain of reasoning was coherent).

### T2.7 — Abort kill-switch ✗ REGRESSION

POST `/abort` on a plan with `status='proposed'` returns **500 Internal Server Error**.

Root cause traceback (full stack in `/private/tmp/.../api.log`):
```
File "packages/api/src/api/repo/research.py", line 58, in _row_to_plan
    return Plan(...)
pydantic_core._pydantic_core.ValidationError: 1 validation error for Plan
status
  Input should be 'draft', 'approved', 'running', 'complete', 'aborted',
  'failed' or 'superseded'
  [type=literal_error, input_value='proposed', input_type=str]
```

**This is the same root cause** as the memory regression above. I added `'proposed'` to the SQL CHECK constraint in migration 017 but forgot to update:
- `packages/api/src/api/types/research.py:17` Pydantic `PlanStatus` Literal
- `packages/frontend/src/features/intelligence/research/types.ts:19` TypeScript `PlanStatus` Literal

Every API route that reads a plan with `status='proposed'` through `_row_to_plan` will 500. Cascading impact:
- `/threads/{tid}/plans/latest` → 500 if latest plan is proposed
- `/threads/{tid}/plans/{pid}/abort` → 500
- `/threads/{tid}/plans/{pid}/steps,findings,notes,subagent-calls` → 500 (all use `_authorize_and_get_plan`)

**Wrong-user abort correctly returns 403** when the underlying plan is readable (not 500-blocked).

## Frontend (Tier 3+4+5)

14/16 Playwright tests in `comprehensive-e2e.spec.ts` pass. The 2 fails are test-design selector specificity issues (matched multiple elements), NOT real regressions — screenshots in `packages/frontend/test-results/comprehensive-e2e-*/test-failed-1.png` confirm the actual app renders correctly.

**Verified working:**
- ✓ All 4 dashboards load + show heading + render data without crashes
- ✓ Past-due dashboard uses pseudonymous officer names (no PII leak)
- ✓ Chat input accepts text + maintains value
- ✓ Dashboard partial-data: heading still renders (HUG-240 fix holds)
- ✓ Dashboard 500: role=alert visible (graceful error)
- ✓ Network abort: heading + alert still render
- ✓ `/approve` direct API call: 4xx (confirms Phase B deletion)
- ✓ `/abort` direct API call: 4xx with bogus plan_id (route alive)
- ✓ Root URL loads with headings

**NOT exercised this run** (sub-scope deferred from HUG-245):
- PlanPreview Approve button click flow (frontend still wires it; will surface a user-visible 404 if clicked when a plan exists)
- ResearchAuditPanel rendering subagent_calls (still wired to legacy `useGetResearchStepsQuery` → returns empty for new plans)
- SubagentCallList component (shipped, but not wired into any visible UI surface)
- Chat full SSE round-trip render in the browser (validated via curl in Tier 2)

## Observability (Tier 6)

| Surface | Result |
|---|---|
| structlog events emitted | ✓ `agent.turn_started`, `agent.tool_call`, `repo.research.get_plan`, etc. all present in `/tmp/hughes-test-logs/api.log` |
| Vector pipeline | ✓ `:8686/health` 200 |
| Prometheus counters scraped | ✓ all expected counter names present (`hughes_agent_turn_duration_seconds_*`, `hughes_research_plan_versions_total`, `hughes_research_subagent_spawns_*`) |
| Victoria-Logs reachable | ✓ `:9428/` 200 |
| Victoria-Metrics reachable | ✓ `:8428/` 200 |
| Jaeger reachable | ✓ `:16686/` 200 |
| list_metrics lru_cache active | ✓ confirmed via fresh-process probe (each Python process has its own cache; API's in-process stats not introspectable from outside) |

Counter values were reset between tests by API restarts (mf-PATH fix + stderr-capture restart). The pipeline shapes are correct; runtime values aren't meaningful in this run.

## Decision matrix — every finding classified

| # | Finding | Class | Severity | Where | Action |
|---|---|---|---|---|---|
| 1 | `PlanStatus` Literal missing `'proposed'` | ✗ regression | P0 | `api/types/research.py:17` + `frontend/.../research/types.ts:19` | **Fix now.** Trivial: add `"proposed"` to both Literal types. Migration 017 already permits it server-side. |
| 2 | `write_memory` FK violation; memory writes always fail | ✗ regression | P0 | `api/services/lead_agent.py:93` (placeholder uuid4() doesn't FK research_plans) | Fix path: either (a) drop FK on `research_lead_notes.plan_id`, or (b) resolve plan_id dynamically inside memory tools via `get_latest_plan(thread_id)`. Option (b) is cleaner. |
| 3 | HUG-245 deferred frontend regressions (Approve button → 404, AuditPanel uses legacy hooks, SubagentCallList unwired) | 🔧 expected-broken | P1 | `frontend/src/features/intelligence/research/{PlanPreview,ResearchAuditPanel}.tsx` | Already documented in `docs/sessions/2026-05-16-decommission-audit.md` as Phase-B deferred. User decides priority. |
| 4 | `GET /threads/{tid}` has no ownership check | ⚠ pre-existing | P0 (security) | `api/routes/threads.py:208-221` | **Fix now** independently of the autonomous run. Add `if thread.user_id != _user_id(...): raise HTTPException(403)`. Same for `post_message` at line 224. |
| 5 | `mf` binary shadowed by TeXLive's METAFONT | ⊘ env | n/a | local PATH only | Document in dev README; not a code issue. |
| 6 | Playwright suite 2/16 fail (selector specificity) | ⊘ test | n/a | `comprehensive-e2e.spec.ts:88,96` | Test-side fix: tighten selectors. Not a product regression. |
| 7 | Phase B CI + NL Eval green; lead-agent accuracy holds at 95.8% must-pass | ✓ pass | — | n/a | Confirms decommission did not break chat accuracy. |
| 8 | Lead-agent simple-question discipline (ANCHOR-F) | ✓ pass | — | `lead_agent_prompt.py` | T2.1 confirmed: no over-use of heavy tools. |
| 9 | Lead-agent deep-question full stack: propose_plan + run_subagent + SSE + persistence | ✓ pass | — | end-to-end | T2.2 confirmed: 2 propose_plan, 5 run_subagent, 3 subagent_calls rows, real synthesised answer. |
| 10 | All 4 dashboards render (full + partial + 500 + abort + slow) | ✓ pass | — | frontend | HUG-240 partial-data fix holds. |
| 11 | All backend routes exist with expected status codes | ✓ pass | — | `routes/*.py` | Excluding the threads-ownership pre-existing bug. |
| 12 | `/approve` returns 404 (deleted in Phase B) | ✓ pass | — | n/a | Confirms Phase B deletion intent. |
| 13 | Telemetry pipeline (structlog + Prometheus + Vector + Victoria-* + Jaeger) | ✓ pass | — | observability stack | All endpoints respond; counter shapes correct. |

## Recommended fixes (proposed order)

**P0 — fix immediately (small, isolated, no NL Eval risk):**

A. **PlanStatus Literal update** (2-line fix in 2 files). Unblocks `/abort`, `/plans/latest`, `/abort`, every plan-reading GET when latest plan is `proposed`. No NL Eval impact (doesn't touch agent/runner/llm).

B. **threads.py ownership checks** (pre-existing P0 security gap). Add user_id check in `get_thread` + `post_message`. No NL Eval impact.

**P0 — fix soon (requires careful design):**

C. **`write_memory` plan_id resolution.** Change `stream_lead_turn` to either drop the FK or resolve plan_id dynamically. Touches `services/research_agent` indirectly via `memory_tools.py` paths — will fire NL Eval, but the change is small.

**P1 — frontend Phase-C completion:**

D. **PlanPreview reframe + ResearchAuditPanel hook swap + SubagentCallList wiring.** Per HUG-245's deferred sub-scope. Frontend-only — no NL Eval trigger. Probably 1-2 days of focused work.

**P2 — opportunistic:**

E. Tighten the 2 flaky Playwright selectors in `comprehensive-e2e.spec.ts`.

F. Document `mf` PATH-prepend in the dev setup README.

## Files referenced in this verification

- Logs: `/tmp/hughes-test-logs/{tier0_baseline,tier1_routes,tier6_observability,api,sse_capture*}.txt`
- T2 SSE captures: `/tmp/hughes-test-logs/tier2_lead_agent/t2{1,2}/sse.txt`
- Playwright reports: `packages/frontend/test-results/` and `packages/frontend/playwright-report/`
- Test scripts: `/tmp/hughes-test-logs/{tier1_smoke,tier2_t21_simple,tier2_t22_deep}.sh`

## End-of-verification status

**The autonomous run delivered a working integrated product** modulo the 3 regressions classified above. The lead-agent path works end-to-end against the real LLM with proper SSE streaming, tool dispatch, persistence, and graceful failure recovery. ANCHOR-F prompt discipline is holding (simple questions don't over-use heavy tools). NL Eval did not regress.

The 2 P0 regressions are both small and isolated, and the P0 pre-existing security gap is independent of the autonomous run. Once those three are addressed (Items A, B, C above), the product is in a defensible shippable state.

The frontend's HUG-245 deferred sub-scope (Item D) is the only remaining substantial work, and it's frontend-only — no NL Eval risk, can be developed and validated incrementally.
