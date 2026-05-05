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
