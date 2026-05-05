# ADR-0003: Data Intelligence v2 — conversational + MetricFlow + ChartSpec

**Date:** 2026-05-05
**Status:** Accepted
**Linear epic:** HUG-172

---

## Context

The current Data Intelligence module is a one-shot question-answering surface:
a single `POST /ask` returns a single answer derived from free-form, LLM-generated
SQL grounded by ~2K lines of prose YAML
(`packages/nl-engine/context/{schema_context,metrics,examples,rules}.yaml`). The
LLM is **Qwen 3 235B on Cerebras** (CLAUDE.md previously said "Gemma 4 (Google AI
Studio)" — corrected in this commit). [_Note added 2026-05-05: this LLM choice
is **superseded by ADR-0004**, which switches both `engine.ask` and the agent
to Qwen 3 32B on Groq. See Decision #8 below + ADR-0004._] There is no thread, no follow-up, no
clarification round-trip; the chart surface auto-detects line vs. table from
the result schema (`packages/frontend/src/features/chat/messages/ResultRenderer.tsx`)
and cannot render anything richer.

This ADR captures the architectural decisions for evolving all three layers
together.

## Decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Conversation state | Server-side Postgres `threads` + `thread_messages` tables. Frontend hydrates on load via `GET /threads/{id}` |
| 2 | API compat | `/ask` stays as a stateless one-shot. New `/threads` + `/threads/{id}/messages` live alongside |
| 3 | Semantic layer | dbt MetricFlow — full migration, including entity-level fact tables as semantic models so MF can serve aggregations *and* row-level lookups (no free-form SQL escape hatch in steady state) |
| 4 | Agent framework | LangGraph + `PostgresSaver` checkpointer. Adapter at the persistence boundary translates LangChain `BaseMessage` ↔ canonical `{role, content, tool_calls, tool_results}` JSON; LangChain types are contained inside graph nodes |
| 5 | Agent pattern | Tool-calling ReAct on top of LangGraph's `create_react_agent`, extended with: hard step cap of 10 LLM calls per turn; a typed terminal `final_answer` tool returning `{summary, chart_spec?, rows?, mf_query?}`. Tools: `list_metrics`, `lookup_metric_definition`, `mf_query` (with internal max-2 retry on validation failure), `clarify`, `render_chart_spec`, `final_answer` |
| 6 | Charts | Closed-set Pydantic `ChartSpec` (`type: 'kpi'\|'line'\|'bar'\|'stacked_bar'\|'donut'\|'table'`, x, y[], groupBy?, format, title) → frontend `<ChartRenderer spec={spec}/>` switch into Recharts. Validated server-side before send. Vega-Lite escape hatch deferred until needed |
| 7 | DSPy | Deferred. Build the eval set as a deliverable of HUG-180; bring DSPy in as HUG-181 follow-up once ≥50 labeled examples exist |
| 8 | LLM | ~~Stay on Qwen 3 235B (Cerebras).~~ **Superseded by ADR-0004 (2026-05-05): Qwen 3 32B on Groq Cloud.** The original rationale (rate-limit risk acknowledged but accepted) was overturned by the first end-to-end eval run, which showed the 5-RPM ceiling is incompatible with multi-turn ReAct under any realistic workload. See `0004-llm-switch-qwen3-32b-groq.md`. |
| 9 | Streaming | Server-Sent Events via `sse-starlette` for agent step-by-step progress to the frontend. No WebSocket |
| 10 | Auth | Out of scope this epic. Use existing per-tab session header as the thread owner. Future ticket for auth + thread ACLs |

## Why these choices

### Why MetricFlow over free-form SQL
dbt's 2026 benchmark (`docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026`)
shows raw text-to-SQL at 84–90% accuracy vs. semantic-layer-routed at 98–100%
on the same questions. The agent emits a constrained MetricFlow query JSON
(`{metric, dimensions, where, time_grain}`) that compiles to verified SQL —
hallucinated joins are impossible, the whitelist is "metrics that exist."
We accept the upfront translation cost (~30 metrics × 30–60 min each) for
durable accuracy gains.

### Why entity-level fact tables as semantic models too
MetricFlow can serve dimension-only queries when no metric is requested,
which covers row-level questions ("list 5 largest auto loans with member name
and dealer name") that aren't aggregations. By modeling `dim_loan`,
`dim_member`, `dim_dealer`, `dim_household` as semantic models with entities
+ dimensions but no measures, we make the catalog complete and avoid a
parallel free-form-SQL highway.

### Why LangGraph over Pydantic-AI / plain Python
LangGraph ships a maintained `create_react_agent` recipe and a first-class
`PostgresSaver` checkpointer that wires thread persistence with no
hand-rolling. The LangChain message-type "leak" is contained inside graph
nodes — we adapt to/from our canonical JSON at the persistence boundary
(~50 lines of mapping). Pydantic-AI was the close runner-up; we'd revisit
only if LangGraph's PostgresSaver schema becomes painful.

### Why ReAct over Plan-and-Execute
Chosen for flexibility on open-ended follow-ups (e.g., "explain why
delinquency spiked"). The trade-off is reduced eval reproducibility (varying
step counts) and higher rate-limit pressure. We mitigate both by:
- step cap of 10 (hard liveness guarantee)
- typed terminal `final_answer` tool (every turn produces an artifact we can
  diff, similar to a Plan in Plan-and-Execute)
- ReAct-appropriate scoring in HUG-180: grade on the terminal `final_answer`
  shape, not the path
- collapsing render-chart and summarize into the single `final_answer` tool
  (drops a hop)
- caching `list_metrics` + `lookup_metric_definition` in-process

### Why a closed-set ChartSpec over LangChain Generative UI / Vercel `ai/rsc`
Both Generative-UI runtimes assume Next.js + RSC; we're on Vite + RTK Query.
Beyond stack fit, a constrained Pydantic spec means: no LLM-generated React,
no eval, no remote code; every chart is reproducible from a JSON blob in
the audit log; structural tests can assert the spec shape. Vega-Lite stays
documented as an escape hatch for the rare spec the closed set can't
express, but isn't shipped this epic.

### Why DSPy is deferred
DSPy compiles prompts against a labeled eval set. The eval set is itself a
deliverable of HUG-180 (50+ multi-turn examples with ground-truth
`final_answer`s). Adopting DSPy on day 1 means optimizing prompts before we
know which ones matter. Folding it in as HUG-181 is a 1–2 day spike with
~5–15% accuracy lift on top of finished work.

## Consequences

- **Existing dashboards keep working** — they hit `/dashboards/*` mart-backed
  endpoints, untouched. The chat UI migrates to `/threads`; `/ask` remains for
  programmatic callers (eval scripts, integration tests) on a clear deprecation
  runway.
- **MetricFlow becomes the single source of truth for metric definitions.** The
  prose `metrics.yaml` deprecates over time as `metrics.yml` becomes
  authoritative; we'll keep both in sync until HUG-181 lands.
- **Audit log gets richer.** Every tool call + tool result lands as a row in
  `thread_messages`; the full reasoning trace is replayable.
- **Cerebras rate limit is the operational risk.** Tracked in HUG-180; if it
  bites, the escalation path is to swap small-model calls (`render_chart_spec`)
  to a local Gemma/Phi-mini.

## Out of scope

- Auth + thread ACLs (future epic)
- Live multi-user collaboration on a thread
- Vega-Lite escape hatch (deferred until a missing-spec request justifies it)
- Translating dashboards to MetricFlow (they keep their typed mart endpoints)
- Cross-thread context (each thread is isolated; no "remember what I asked
  last week")

---

## Amendment 2026-05-05 — Decision #6 swapped: hand-rolled ChartSpec → OpenUI

### What changed

Decision #6 originally specified a closed-set Pydantic `ChartSpec` (`type: 'kpi' | 'line' | 'bar' | 'stacked_bar' | 'donut' | 'table'`) rendered by a frontend `<ChartRenderer/>` switch. **That decision is replaced by OpenUI** (`@openuidev/react-lang` runtime + `@openuidev/react-ui/genui-lib`'s standard 54-component library):

* Agent emits OpenUI Lang DSL into `final_answer.openui_dsl` (HUG-178 Phase B wires this).
* Server parses + validates the DSL via a Node subprocess wrapping the OpenUI parser (HUG-178 Phase B).
* Frontend renders via `<OpenUIRenderer dsl={...} />`, a thin wrapper around `@openuidev/react-lang`'s `<Renderer>` with an error boundary (HUG-178 Phase A — done).

### Why the swap

* **Capability ceiling.** The hand-rolled ChartSpec covered ~6 chart variants. OpenUI's `openuiLibrary` ships 54 typed components (Stack, Card, Table, LineChart, BarChart, PieChart, RadarChart, ScatterChart, Form/Input, Tabs, Accordion, Steps, etc.) all built on Recharts (the same lib we already use). Wider visual palette without a parallel viz stack.
* **Validated feasibility.** The HUG-178 Day-1 spike (HUG-195's escalation evaluation, Step 1) measured **19/20 = 95% DSL validity** on must-pass questions via Gemma 4 31B + the standard `openuiLibrary`. Above the 90% threshold; first-attempt, no few-shot. Spike report attached to HUG-195.
* **Safety profile preserved.** Zero LLM-generated executable code reaches the browser — the OpenUI parser only dispatches to registered components by name, props are Zod-validated, no `eval`, no `dangerouslySetInnerHTML`. Same constraint that motivated the original closed-set ChartSpec.

### What's NOT changed

* All other ADR-0003 decisions stand: `/threads` + `/threads/{id}/messages` SSE surface, server-side conversation persistence (Postgres), LangGraph + `PostgresSaver`, ReAct agent with hard step cap of 10, MetricFlow as the metric-truth substrate, no free-form SQL escape hatch in steady state.
* The `final_answer` tool's `openui_dsl: str | None = None` field shape — already wired in HUG-176, just unused until HUG-178 Phase B turns the agent's prompt instruction on.
* The agent's tool-calling and tool descriptions — Phase B updates the `final_answer` tool docstring and prepends a system prompt; tools themselves are unchanged.

### Phasing

* **HUG-178 Phase A (this commit):** scaffolding only — npm deps, `library.ts` re-export, `OpenUIRenderer.tsx` component with error boundary, `openui.py` Pydantic envelope. Production behavior unchanged because agent doesn't yet emit DSL.
* **HUG-178 Phase B (follow-up):** agent system prompt injection, Node-subprocess DSL validator wired into `agent_runner.py`, 5-question runtime smoke test before merge, `final_answer` tool docstring update.

### Rejected options (recorded)

* **Stay on hand-rolled ChartSpec.** Would have shipped faster but capped the agent's visual expressiveness at 6 chart types. The HUG-195 spike demonstrated OpenUI's higher ceiling is achievable in practice; staying on ChartSpec would forfeit that without a corresponding gain.
* **Hosted Thesys C1 API.** Vendor lock-in + paid tier; rejected at original ADR-0003 time. Re-confirmed.
* **Per-component custom OpenUI library.** HUG-178's Day-1 spike tried a 3-component custom library and scored 5% — OpenUI's prompt template hard-codes `Root`/`Stack` as expected components, which custom libraries don't register by default. Switching to the standard library fixed the issue at zero cost. The custom-library path is rejected.

### References

* HUG-178 (this ticket) — the production-integration umbrella.
* HUG-195 — the escalation evaluation that produced the 95% measurement.
* HUG-196 — the multi-provider LLM factory (Groq + Google AI Studio) that enabled the spike to run on Gemma 4 31B without waiting for Groq quota.

---

## Amendment 2026-05-05 (Phase B) — agent emits OpenUI DSL + server-side validator

### What changed

The HUG-178 Phase A amendment above promised a Phase B follow-up that turns the rendering substrate on. That follow-up has now landed:

* **Agent system prompt.** A 20K-character OpenUI Lang reference is now prepended (transiently per call) to every LangGraph turn. The committed artifact at `packages/nl-engine/src/nl_engine/agent/openui_prompt.txt` is regenerated via `make openui-prompt`, which invokes `packages/frontend/scripts/generate-openui-prompt.mjs` against the standard `openuiLibrary`. A tool-calling preamble re-frames the OpenUI prompt's "respond with raw DSL" framing — DSL goes inside `final_answer.openui_dsl`, never as the message body.
* **`final_answer` tool docstring.** Now instructs the agent to populate `openui_dsl` whenever a chart/table/KPI tile communicates the answer better than prose, and to leave it None for purely textual answers.
* **Server-side validator.** `packages/api/src/api/services/openui_validator.py` spawns `packages/frontend/scripts/validate-openui-dsl.mjs` as a Node subprocess on every terminal turn that carries `openui_dsl`. The script imports `@openuidev/react-lang`'s `createParser` against `openuiLibrary.toJSONSchema()` and emits `{valid, errors}` JSON. The Python wrapper soft-skips on every failure mode (Node missing, script absent, timeout, non-zero exit, JSON parse error) — the OpenUI parser on the frontend is permissive and the renderer has its own error boundary, so unverified DSL still flows to the browser with `validated=False`.
* **`StreamFinal` schema.** Now carries an optional `openui: OpenUIDslPayload | None` field alongside the persisted `ThreadMessage`. Frontend (HUG-179 territory) reads this to decide whether to render via OpenUI or fall back to the legacy `ResultPanel`.

### Why these specific choices

* **Committed prompt artifact, not boot-time generation.** OpenUI's instruction manual is a JS function (`openuiLibrary.prompt(openuiPromptOptions)`). Three options were considered: (a) commit the artifact, (b) shell out to Node at API boot, (c) write a custom shorter prompt. Chose (a) — no Node dependency at request time, deterministic, reviewable in git diffs. Drift caught by `tests/structural/test_openui_prompt_drift.py`, which re-runs the generator and compares output. Skipped (not failed) when Node isn't on PATH so backend-only contributors aren't blocked.
* **Soft-skip on validator failure.** The OpenUI parser is permissive and `OpenUIRenderer` has an error boundary. Hard-blocking on validator unavailability would create a Node-dependency in production for marginal safety gain, since the frontend already tolerates malformed DSL. Validation is a defensive signal, not a gate.
* **Tool-calling preamble.** The raw OpenUI prompt opens with "Your ENTIRE response must be valid openui-lang code" — actively hostile to tool-calling. An empirical Q1 against Gemma 4 31B with the unwrapped prompt hit the 10-step cap without ever calling `final_answer`. Wrapping the prompt with our own preamble ("call tools first, put DSL inside `final_answer.openui_dsl`") fixed it on the first re-attempt.

### Smoke test (merge gate, 2026-05-05)

Five must-pass questions (must-pass-001 through must-pass-005, sourced from `packages/nl-engine/benchmarks/questions.yaml`) ran end-to-end through the deployed agent (`LLM_PROVIDER=google`, Gemma 4 31B). Each turn POSTed to `/threads/{id}/messages`, captured the SSE final event, and inspected the attached `OpenUIDslPayload`:

| Question | Validated | Errors | Outcome |
|---|---|---|---|
| Loan-to-deposit ratio | True | 0 | ✅ valid DSL |
| Total loan portfolio balance | True | 0 | ✅ valid DSL |
| Total deposit balance | True | 0 | ✅ valid DSL |
| Rate spread | True | 0 | ✅ valid DSL |
| Past-due ratio | True | 0 | ✅ valid DSL |

**5/5 (100%) valid DSL.** Above the 80% merge gate; matches the HUG-195 spike's 95% measurement.

### What's still NOT changed

* Frontend wiring of `<OpenUIRenderer>` into `AssistantMessage.tsx` — HUG-179.
* Streaming DSL rendering, conversation-aware prompt rewriting, retry-on-invalid-DSL — out of scope.
* `final_answer.openui_dsl: str | None` field shape — unchanged from Phase A.
* Tool list or tool call shapes — unchanged.

### Operational notes

* Regenerate the prompt artifact whenever `@openuidev/react-ui` or `@openuidev/lang-core` is bumped: `make openui-prompt`. The structural drift test catches stale artifacts.
* Validator latency: ~50-150ms per terminal turn (Node subprocess startup). Acceptable on SSE turns that take seconds. Defer optimization unless it bites.
* `node` becomes a soft runtime dependency for the API container. If absent, validation soft-skips and DSL still flows; the system continues to function, just without a server-side parse check.
