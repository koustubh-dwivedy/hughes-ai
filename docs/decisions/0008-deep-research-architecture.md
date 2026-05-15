# ADR-0008: Deep Research Architecture

**Status:** Accepted (2026-05-15)
**Authors:** Autonomous execution session per user authorization
**Related:** HUG-201 (Deep Research feature umbrella), HUG-209–HUG-226

## Context

Hughes AI today runs a single LangGraph ReAct agent over MetricFlow +
dbt. It handles "what's our delinquency rate?" cleanly but folds on
"break down past-due exposure by branch × product × vintage and
explain which branches drove the increase YoY." Multi-step
decomposition + synthesis exceeds the chat agent's single-turn
budget.

We need a way to handle deep questions without abandoning the
existing ReAct agent — which is the result of significant prompt-
engineering, DSPy compilation, eval discipline, and operational
hardening.

## Decision

Adopt **Anthropic-style lead + parallel subagents + external plan
memory** with **Topology B** (single backend; planner-led depth;
plan-preview UI for non-trivial plans) and **Schema Option C**
(threads stays the conversation envelope; four new typed tables for
research-specific structure).

Worker subagents ARE the existing ReAct agent, invoked via a
`run_agent_isolated` primitive (HUG-206) with four narrow policy
overrides: empty history, per-step description as user input,
tighter step cap, worker-specific `process_message` callback.

### Architecture summary

```
User question
    ↓
Coordinator
    ↓
Planner LLM (single call, structured JSON)
    ↓
shallow → existing ReAct agent (chat path, unchanged)
    OR
deep    → Persist plan (research_plans)
          ↓
          Emit research.plan.drafted (frontend renders PlanPreview)
          ↓
          User approves/aborts (HUG-212 endpoints)
          ↓
          Expand plan → research_steps rows
          ↓
          Parallel coordinator dispatches workers (HUG-218)
            • Each worker = existing ReAct agent with worker overrides
            • Workers persist to research_findings, not thread_messages
            • Lead writes running notes to research_lead_notes after each batch
          ↓
          Synthesizer: existing ReAct agent invoked one more time
            with the findings as user input + chat-shaped persistence
          ↓
          Final answer lands in thread_messages (symmetric with chat)
```

### Schema (option C)

- `threads` (existing) — conversation envelope; remains the auth anchor.
- `research_plans` — versioned plan documents (`status` enum:
  draft, approved, running, complete, aborted, failed, superseded).
- `research_steps` — typed step rows under a plan.
- `research_findings` — one row per subagent's `final_answer`,
  linked to its step.
- `research_lead_notes` — versioned markdown notes (the "external
  plan memory" primitive).

`ON DELETE CASCADE` from thread → plan → step → finding. Auth
inherits from `threads.user_id`.

## Consequences

### Positive
- **Reuses every minute of work** that went into the existing ReAct
  agent: 5 tools, ANCHOR-A–E system prompt, DSPy-compiled artifacts,
  24/24 must-pass eval discipline. Workers automatically inherit
  improvements.
- **Two product surfaces, one execution stack.** Final answer
  rendering is identical for shallow and deep paths.
- **Auditability.** Every plan version + step status transition +
  finding has an immutable row with `created_at`. Audit trail is a
  cascade-walk from a thread row.
- **Per-role LLM tuning.** `make_llm(role="lead"/"worker"/"verifier")`
  lets each role swap providers/models without code change (HUG-204).

### Negative
- **One extra LLM call per turn** (the planner). Cost not yet
  measured at scale; acceptable for the demo, may need a classifier
  shortcut at production volume.
- **Schema complexity.** Four new tables vs the prior "one JSON
  blob per turn" alternative. JOINs are required for plan→step→finding
  traversal. The repo (`packages/api/src/api/repo/research.py` +
  `research_steps.py`) encapsulates this.
- **Worker context isolation tradeoff.** Each worker re-discovers
  the catalog from scratch (`list_metrics()` lru-cached per process
  mitigates this). A worker can't reuse insights from a sibling —
  the lead has to mediate via `plan_context` + lead notes.
- **Coverage measurement.** New DB-heavy modules drag down the
  no-DB unit coverage % (HUG-234 baseline ratchets). Future: merge
  integration coverage into the gate.

## Alternatives considered

1. **Build a new dedicated deep-research agent from scratch.**
   Rejected: throws away the ReAct agent's investment + eval
   discipline; doubles maintenance surface for marginal gain.
2. **Single agent with longer step cap.** Rejected: context
   window explodes; the agent loses coherence past ~6 steps.
3. **Topology A (separate backend stack for deep-research).** Rejected:
   diverges the streaming/persistence surface from chat. Topology B's
   "planner is first node of the unified coordinator" keeps one
   funnel.
4. **Schema Option A (one JSON blob per turn, no typed tables).**
   Rejected: every "what's the latest plan version" query becomes a
   JSON scan; re-plans, audit views, and step-state queries all
   become awkward. Option C is verbose but every operation is one
   typed query.
5. **Schema Option B (one row per turn with denormalized
   steps/findings).** Rejected: same JSON-scan problem on a smaller
   surface; doesn't compose with re-plan (which needs versioning).

## Implementation phases

Tracked under HUG-201 with sub-issues HUG-202 through HUG-226.

- **Foundation** (HUG-202–207): schema migration, repo CRUD,
  `make_llm` per-role, coordinator skeleton, telemetry primitives,
  `run_agent_isolated` extraction.
- **Lead** (HUG-208–212): planner LLM, plan persistence + SSE,
  frontend RTK, PlanPreview UI, approve/abort endpoints.
- **Execution** (HUG-213–218, S1+S2 split): step lifecycle, worker
  wrapper, sequential then parallel executors, finding persistence,
  final synthesis.
- **External memory** (HUG-220–222): lead notes, re-plan logic,
  plan.revised SSE + UI handling.
- **Polish + verification** (HUG-223–226): Reflexion-style verifier
  (opt-in), audit-trail UI, this ADR, Playwright e2e.

## CI considerations

Deep Research lands against the CI hardening baseline introduced
in HUG-227 (Phase B of the autonomous-execution session):

- Migration loop globs `migrations/*.sql` (HUG-228), so adding
  table 016_research_tables didn't require a CI edit.
- `@pytest.mark.db` marker (HUG-229) routes the new DB-backed
  research tests to the integration job.
- SSE event-contract gate (HUG-231) pins the wire shape via golden
  trace files (`packages/api/tests/golden/research_deep_turn.txt`).
- Backend↔frontend type-drift gate (HUG-232) catches Pydantic
  changes to `api.types.research` without matching frontend updates.
- Coverage gates (HUG-234) ratcheted twice during the session to
  accommodate DB-heavy modules; baseline at api=63 today.

## Amendment to ADR-0004 (LLM provider)

HUG-204 extended `make_llm()` to accept an optional `role` parameter
(lead / worker / verifier). The single-LLM default rule still applies
— `make_llm()` with no role returns the canonical model. The role
override is opt-in via `roles:` block in `config/llm.yaml` and used
only by the Deep Research surface.

This is a strict superset of ADR-0004's policy: no existing call
site is forced to use roles; the default behaviour for chat,
dashboards, eval is unchanged.

## References

- Anthropic's published lead+subagents pattern (the canonical
  external description of the architecture this ADR adopts).
- Migration: `migrations/016_research_tables.sql`.
- Repo: `packages/api/src/api/repo/research.py`,
  `packages/api/src/api/repo/research_steps.py`.
- Services: `packages/api/src/api/services/research_agent/`.
- Frontend: `packages/frontend/src/features/intelligence/research/`.
- Session log capturing the implementation decisions:
  `docs/sessions/2026-05-15-autonomous-execution.md`.
