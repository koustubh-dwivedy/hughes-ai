# ADR-0006: Tool docstrings and Field descriptions in `agent/tools.py` are production prompts

**Date:** 2026-05-10
**Status:** Accepted
**Linear epic:** HUG-172
**Linear issue:** HUG-200 (root cause), follow-up TBD

---

## Context

On 2026-05-06 (commit `0cdf3fa`) the agent scored 20/24 (83.3%) on
the must-pass eval. On 2026-05-10 the same eval — same LLM
(Ollama GLM-5.1), same questions, same prompt — scored 10/24 (41.7%).

A forensic git diff narrowed the regression to commit `35baee6`,
labelled "feat(observability): structured logging for HUG-200." The
commit's stated purpose was telemetry. In the same diff, however, the
prose of several docstrings and Pydantic `Field(description=...)`
strings inside `packages/nl-engine/src/nl_engine/agent/tools.py` was
silently shortened. Specifically:

- `mf_query.__doc__` lost its worked dimension/order/filter examples
  and the explicit "do not paraphrase" warning.
- `MfQueryArgs.dimensions.description` lost its "MUST copy verbatim"
  guidance and the concrete examples that disambiguate
  `deposits_monthly_grain__branch` vs `branch`.
- `MfQueryArgs.where.description` lost its multi-example Jinja
  format guidance.
- `MfQueryArgs.order.description` lost the "NEVER use ASC or DESC"
  warning that prevents a class of MetricFlow rejections.
- `final_answer.__doc__` lost the OpenUI DSL guidance.

Per-question forensic analysis confirmed the dominant failure mode
(10 of 14 regressions) was the agent picking valid-but-wrong
dimensions like `ncua_5300_line_code` instead of `product_name` —
exactly what those guidance strings had been preventing.

## Why this happened

LangChain's `bind_tools()` serializes a function's docstring and any
Pydantic `Field(description=...)` strings into the JSON tool schema
the LLM receives. When the LLM decides *what* to call and *what
arguments to pass*, those strings are part of the prompt — same as
the system prompt, same as the user message. **Treating them as
documentation that can be tightened for readability is a category
error.**

The HUG-200 commit was reviewed for telemetry correctness. No one
flagged the prose changes because, syntactically, they were just
docstring edits. The eval was not re-run on the merging branch
because docstring-only changes look behaviourally inert.

## Decision

1. **Tool docstrings and `Field(description=...)` strings on
   anything inside `agent/tools.py` are production prompts.** They
   are part of the LLM's input on every call. Any change to their
   prose is a behaviour change.

2. **Changes to those strings require:**
   - A re-run of the must-pass eval before merge.
   - A line-by-line diff review specifically for prompt content (not
     just formatting / lint compliance).

3. **A regression test is in place** to mechanically catch silent
   trims. `packages/nl-engine/tests/test_tool_docstring_invariants.py`
   asserts the presence of specific load-bearing phrases ("verbatim",
   "NEVER paraphrase", explicit semantic-ID examples, ASC/DESC ban,
   etc.) and a minimum length on the most failure-prone strings.

   When that test fails, its message is intentionally instructional:
   *"This docstring is a production prompt, not just documentation.
   The LLM reads it as instructions. If you intentionally want to
   change it, update this test AND re-run `make eval` before
   merging."*

4. **Code under `agent/tools.py` is split**: anything that does not
   need to be visible to the LLM (retry logic, telemetry helpers,
   error classification) lives in
   `agent/mf_query_runner.py`. This frees LOC headroom under the
   300-line cap so the prompt-bearing strings never need to be
   trimmed for size reasons.

   **Rule:** when `tools.py` exceeds the cap, move CODE out, never
   PROMPT out.

## Consequences

### Positive

- A future contributor cannot trim a load-bearing phrase without
  the test failing immediately.
- The "this is a prompt" framing makes review easier — the diff
  hunks worth reviewing carefully are the prose ones, not the
  telemetry ones.
- Splitting code from prompt clears the structural cap as a
  scapegoat reason to shrink the docstrings.

### Negative

- The invariant test has to be maintained alongside the docstrings.
  When prose intentionally changes, two files change.
- The split between `tools.py` and `mf_query_runner.py` is asymmetric
  — `tools.py` imports private-named helpers, which is mildly
  unidiomatic. Acceptable trade-off: the import surface is private
  by intent (one module, one consumer).

### Operational

- Eval drops below 80% trigger a forensic that includes diffing
  recent commits for prose changes in `agent/tools.py` and
  `agent/system_prompt.py` even when the commits don't claim to
  touch prompts.

## Out of scope

- The `system_prompt.py` file already follows this principle by
  convention — every change to it is reviewed as a prompt change.
  This ADR does NOT add new mechanical guardrails on it; the
  invariant test is scoped to `tools.py` only because that is where
  the regression happened.
- Long-tail eval threshold remains 65%; not changed by this ADR.

## References

- `git show 35baee6` — the regressing commit.
- `git show 0cdf3fa` — the last passing commit before the regression.
- `packages/nl-engine/tests/test_tool_docstring_invariants.py` —
  the mechanical guardrail.
- `packages/nl-engine/src/nl_engine/agent/mf_query_runner.py` —
  the extracted helpers.
- ADR-0007 — companion ADR on catalog and eval-quality discipline.
