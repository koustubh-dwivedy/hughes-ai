# ADR-0005: DSPy prompt compilation — scaffolding shipped, integration deferred

**Date:** 2026-05-09
**Status:** Accepted
**Linear issue:** HUG-181
**Predecessors:** HUG-188 (grader rewrite), HUG-189 (in-process agent runner)

---

## Context

HUG-181 proposed compiling the agent's prompts via DSPy against the labeled
eval set, replacing hand-written templates with optimized artifacts and
verifying a 5–15% accuracy lift. The thesis: hand-written prompts are a
local maximum and DSPy treats prompt selection as a search problem that
typically yields measurable lift on text-to-SQL / RAG / agentic benchmarks.

Phase 1 of the work shipped the scaffolding (commit `7f5df2f`):

- 5 DSPy modules (`PlanQuestion`, `MetricFlowQueryWriter`, `RenderChartSpec`,
  `Summarize`, `Clarify`) with hand-written `Signature` instructions.
- `prompts/loader.py` returns `None` for missing/broken artifacts so the
  runtime falls back to the hand-written template — every code path is safe
  whether or not artifacts exist.
- `scripts/compile_prompts.py` opt-in compiler over `BootstrapFewShot`.
- `.github/workflows/nl-prompt-compile.yml` weekly cron, currently
  `disabled_manually`.
- 8 unit tests covering module construction + loader fallback paths.

What was outstanding when this ADR was written: actually running the
compile script, wiring the artifacts into the live runtime, and proving
≥5% lift via `make eval`.

## Probe — Phase 2a, 2026-05-09

Ran the compile script end-to-end against an 8-row subsample (Groq free
tier 6K TPM dictates the size) on Qwen 3 32B. Bug-fixes landed in the
script during the probe — distinct trainset builders per module, a
module-aware metric (only `PlanQuestion` has a real label, the other four
use a no-signal pass-through), and `COMPILE_SAMPLE_SIZE` env-var control.

Five artifacts were produced. Qualitative inspection:

| Module | Status | Finding |
|---|---|---|
| `plan.json` | ✅ Usable | 8/8 demos correctly map question → `query_data`. |
| `summarize.json` | ❌ Unusable | Every demo has `rows: '[]'`; the LLM learned to **echo the question as the summary** because the trainset never provided real row data. |
| `mf_query_writer.json` | ⚠️ Partial / wrong shape | 3/8 demos got real metric names but with bare dimension strings (e.g. `["channel"]`) instead of MetricFlow's required semantic IDs (`application__channel`). Wiring this in would feed the agent malformed dimensions. |
| `render_chart_spec.json` | ⚠️ Degenerate | All `chart_spec: ''` — no signal. |
| `clarify.json` | ⚠️ Degenerate | All `clarification: ''`, `options: '[]'` — no signal. |

Only `PlanQuestion` produced a usable artifact, and the live ReAct agent
in `graph.py` does not call `PlanQuestion` — it routes via tool-calling
on the LangChain `BaseChatModel`. So the one good artifact has no
production consumer and the four artifacts with potential consumers are
not safe to use.

## Decision

**Defer DSPy integration. Close HUG-181 with the scaffolding in place
and the probe artifacts committed as evidence.** The acceptance criteria
explicitly allow this path: *"or a written explanation in the PR
description for why we keep / drop DSPy if the lift is smaller."*

This is a judgement about codebase and product stage, not a judgement
about DSPy as a tool.

## Why now is the wrong time

**The current production prompt is hand-crafted and earns its lift from
domain rules, not few-shot demos.** `system_prompt.py` (~220 lines)
encodes the ANCHOR rules from HUG-190 — concrete instructions like
"ALWAYS call `list_metrics` before `mf_query`" and "use the catalog's
exact dimension strings, not user-friendly paraphrases." These are
rules a hand-iteration loop discovered from watching specific failure
modes; they're not patterns that fall out of sampling demos. The 83.3%
must-pass result on the promotion ledger row `0cdf3fa` is owned by
those rules.

**The eval set isn't shaped for DSPy bootstrapping.**
`benchmarks/questions.yaml` carries ground-truth SQL and expected
keywords, but no per-module labels: there's no "expected metric name"
for `MetricFlowQueryWriter`, no "expected summary" for `Summarize`, no
"expected ambiguity" for `Clarify`. DSPy's `BootstrapFewShot` needs
that kind of signal to find good demos. The probe confirmed what was
already evident from inspecting `questions.yaml`: with the current
schema, only `PlanQuestion` (action label = `query_data`) gets any
useful signal.

**The two architectures don't compose without surgery.** The 5 DSPy
modules are shaped for a plan-execute pipeline (decide action →
dispatch to a specialist → produce output). The live agent is a
LangGraph ReAct loop with one shared system prompt and tool-calling.
Wiring DSPy into the live path would mean either replacing the ReAct
loop (high risk, multi-day work, real chance of regressing below the
80% gate) or limited integration of one module (`Summarize`) in a way
where the qualitatively-broken demos in `summarize.json` would
actively hurt accuracy. Neither is a small change to a working system.

**At our current scale, the maintenance economics favor hand-prompts.**
DSPy's strength is sub-linear scaling of prompt maintenance as
question patterns, LLM providers, and use cases multiply. We have
70 eval questions, one CU, one LLM at a time (locked by ADR-0004),
and a hand-iteration loop that completes in minutes. The crossover
point where DSPy starts paying for itself isn't here yet.

## What stays

- The 5 DSPy modules in `agent/prompts/` (Phase 1 scaffolding).
- The runtime loader's safe-fallback semantics (every code path
  works whether or not artifacts exist).
- `scripts/compile_prompts.py` (with the bug-fixes from this probe —
  distinct trainset builders, module-aware metrics, sample-size
  control). Re-runnable in seconds when the trigger conditions below
  fire.
- `.github/workflows/nl-prompt-compile.yml` weekly cron, still
  `disabled_manually`.
- The 5 compiled artifacts under `prompts/compiled/`. Committed as
  evidence of the probe — they are NOT safe to load into the live
  agent without a stronger trainset.

## What removes the deferral

Re-open this work when any of the following happens:

1. **Onboarding CU #2** with its own metric catalog. Per-CU prompt
   compilation is exactly DSPy's sweet spot.
2. **Swapping LLM providers** more frequently than the hand-prompt
   tunes for. The Gemma 0/12 result during HUG-190 is the canary —
   if we hit that pattern again, DSPy's recompile-against-new-LM
   capability becomes load-bearing.
3. **Eval set crossing ~300 questions**, where hand-rule maintenance
   gets painful and a search-based approach wins on time-to-coverage.
4. **A/B-testable prompt variations** become a regular need (today
   they aren't — every prompt change is a single edit in
   `system_prompt.py`).

## What unblocks DSPy when we re-open

Before any of the above triggers, the data work needed is:
**grow `questions.yaml` so each row carries `(metric, dimensions,
where, summary)` ground-truth labels per module**, not just SQL.
That's a multi-day curation effort and would deserve its own ticket.
Until that data exists, every compile run will produce the same
weak artifacts the probe found.

## Consequences

**Positive.** Working production path is unchanged. No risk of
regressing the 83.3% must-pass result. The scaffolding sits dormant
on disk at zero ongoing cost. Future re-opening has a clear,
documented runway.

**Negative.** The 5–15% lift the original ticket hypothesized is
not realized today. If the assumption "hand-written prompts are a
local maximum" is correct in our case, we are leaving accuracy on
the table — but the probe gave no evidence to support that
assumption at the current scale.

**Neutral.** The hand-prompt approach scales linearly with question
patterns; DSPy scales sub-linearly. The crossover point is somewhere
beyond our current 70 questions; we haven't measured exactly where.
