# HUG-247 Decommission Audit (2026-05-16)

User asked for "extra cautious" handling of HUG-247 with both
audit-trail and review. This doc lists every file that WILL be
deleted in the decommission, every line of production code that
references those files, and every test file that exercises them —
so the actual deletion (Phase B, planned as a follow-up PR) is a
diff with zero surprises.

## Audit-only scope

This HUG-247 commit is **documentation-only**. No code changes, no
flag flip, no file deletions. The deletion happens in a follow-up
PR ("HUG-247 Phase B — execute the decommission") that the user
reviews diff-by-diff.

Rationale: the chat path currently relies on the legacy pipeline
(`coordinator.route_turn`) by default (`RESEARCH_LEAD_AGENT_ENABLED`
defaults to off in HUG-244). Flipping the flag plus deleting code
in one commit would put the chat-question flow through
`LEAD_AGENT_TOOLS` for the first time without a real NL-Eval run
proving that tool surface preserves chat accuracy. That risk is
worth a deliberate review, not an autonomous push.

## Files scheduled for deletion (Phase B)

| File | Lines | Why obsolete |
|---|---|---|
| `packages/api/src/api/services/research_agent/coordinator.py` | ~200 | Routing replaced by `api.services.lead_agent.stream_lead_turn` (HUG-244). |
| `packages/api/src/api/services/research_agent/executor.py` | ~150 | Sequential step executor replaced by lead's `run_subagent` tool (HUG-243). |
| `packages/api/src/api/services/research_agent/executor_parallel.py` | ~120 | Parallel step executor — same. |
| `packages/api/src/api/services/research_agent/planner.py` | ~250 | Pre-LLM plan synthesis replaced by `propose_plan` tool (HUG-242). |
| `packages/api/src/api/services/research_agent/replanner.py` | ~180 | Mid-turn re-planning replaced by `propose_plan` being callable multiple times (HUG-242). |
| `packages/api/src/api/services/research_agent/synthesizer.py` | ~150 | Final-answer synthesis happens inside the lead's own `final_answer` tool call now. |
| `packages/api/src/api/services/research_agent/worker.py` | ~150 | Worker invocation logic replaced by `run_subagent` (HUG-243). |
| `packages/api/src/api/services/research_agent/lead_memory.py` | ~100 | Replaced by `nl_engine.repo.lead_memory` + `read_memory`/`write_memory` tools (HUG-241). |
| `packages/api/src/api/services/research_agent/lead_system_prompt.py` | ~60 | Replaced by `nl_engine.agent.lead_agent_prompt.LEAD_AGENT_SYSTEM_PROMPT` (HUG-244). |

Total: ~9 files, ~1380 LOC.

## Files that SURVIVE (do not delete)

| File | Why kept |
|---|---|
| `packages/api/src/api/services/research_agent/__init__.py` | Package marker. |
| `packages/api/src/api/services/research_agent/events.py` | Event factories `plan_drafted_event` / `plan_approved_event` / `plan_aborted_event` reused by `/approve` + `/abort` routes (HUG-246 keeps both routes for the legacy flow until decommission). |
| `packages/api/src/api/services/research_agent/telemetry.py` | Prometheus counters used by `events.py` + by the lead-agent path. |
| `packages/api/src/api/services/research_agent/verifier.py` | Env-flagged Reflexion check — kept per plan, may be enabled separately. |
| `packages/api/src/api/services/research_agent/worker_process_message.py` | Persistence callback shape reused by the lead path (`run_subagent` writes to `subagent_calls` via the same pattern). |

## Production-code call sites that reference the deletion list

`git grep` evidence (commit 2935ee2):

| Importer | Imports | Phase B action |
|---|---|---|
| `packages/api/src/api/routes/threads.py:17` | `from api.services.research_agent.coordinator import route_turn` | Remove import. Branch is currently flag-gated; flipping `RESEARCH_LEAD_AGENT_ENABLED` default to on and removing the `if lead_agent_enabled():` conditional makes `stream_lead_turn` the only path. |
| `packages/api/src/api/routes/research.py:?` | `expand_plan_into_steps` (from planner/executor for /approve route) | Delete the `/approve` route entirely. The lead-agent path has no approval gate (HUG-246 documented `/approve` as legacy). |
| `packages/api/src/api/services/agent_runner_chat.py:5` (comment only) | references `research_agent/worker_process_message.py` in a docstring | No code change needed; comment is informational. |

Total production-code lines affected by Phase B: ~5-10 (import + dispatch removal + /approve route delete).

## Test files to delete

| Test file | What it tests | Phase B action |
|---|---|---|
| `packages/api/tests/test_research_coordinator.py` | `route_turn` shallow/deep routing | Delete. |
| `packages/api/tests/test_research_coordinator_deep.py` | Deep-route plan persistence | Delete. |
| `packages/api/tests/test_research_executor.py` | Sequential step executor | Delete. |
| `packages/api/tests/test_research_executor_parallel.py` | Parallel step executor | Delete. |
| `packages/api/tests/test_research_findings.py` | Findings persistence (HUG-243 replaces with subagent_calls) | Delete. |
| `packages/api/tests/test_research_lead_memory.py` | Old lead-memory persistence (HUG-241 supersedes) | Delete. |
| `packages/api/tests/test_research_planner.py` | Planner draft generation | Delete. |
| `packages/api/tests/test_research_replanner.py` | Replanner | Delete. |
| `packages/api/tests/test_research_routes.py` | `/approve` + `/abort` endpoint behaviour | **Trim, don't delete.** Keep `/abort` tests; drop `/approve` tests. |
| `packages/api/tests/test_research_synthesizer.py` | Synthesizer | Delete. |
| `packages/api/tests/test_research_worker.py` | Worker subagent invocation | Delete. |
| `packages/api/tests/test_sse_contract.py` | SSE golden trace for chat + deep routes | **Trim.** Drop deep-route golden; keep chat-route. |

Total: 10 full deletes + 2 trims.

## Schema migration to apply (Phase B)

New migration `migrations/019_drop_legacy_research_tables.sql`:

```sql
BEGIN;

-- HUG-247: drop tables made obsolete by the autonomous lead-agent
-- architecture (HUG-241–244). `research_steps` and `research_findings`
-- were the legacy planner/executor's per-step audit trail; the new
-- `subagent_calls` table (HUG-241 migration 017) replaces them.

DROP TABLE IF EXISTS research_findings;
DROP TABLE IF EXISTS research_steps;

COMMIT;
```

Note the order: research_findings has an FK on research_steps, so
findings drop first.

## Feature-flag change (Phase B)

In `packages/api/src/api/services/lead_agent.py:lead_agent_enabled()`,
change the default from `False` to `True`. Even better: rip out the
function entirely and remove the conditional in `routes/threads.py`
so the lead-agent path is the only path.

## CLAUDE.md updates (Phase B)

The "Repo map" section's bullet for
`packages/nl-engine/src/nl_engine/agent/` references "system_prompt.py
+ openui_prompt.txt" — add `lead_agent_prompt.py` to that line. Other
sections that reference the old coordinator/executor/synthesizer flow
need rewording to reflect the autonomous lead.

## Roll-back if Phase B breaks main

```
git revert <decommission-commit-sha>
```

The decommission is one atomic commit. Single revert restores
everything: legacy modules, /approve route, the flag-conditional in
threads.py, and the dropped tables (via re-applying the original
migrations 016 in a fresh DB).

## Verification gate for Phase B

Before merging Phase B:

- [ ] `git grep` for every symbol named in the deletion list returns 0
      hits in non-test, non-doc files.
- [ ] CI green on the full suite (Lint / Typecheck / Unit / Frontend /
      Structural / Integration / E2E / Build).
- [ ] **NL Eval green** (this commit DOES touch
      `services/research_agent/**`, which fires NL Eval per workflow
      path config). Accuracy should NOT regress vs the pre-decommission
      baseline (must-pass 23/24 = 95.8% per HUG-237 on 2935ee2).
- [ ] Manual smoke: feature-flag-on chat question → exercises
      `stream_lead_turn` end-to-end.
- [ ] Coverage gates (api ≥ 63, nl-engine ≥ 75, frontend ≥ 84) hold.

If NL Eval regresses after Phase B, the rollback restores the legacy
flow. Then investigate whether the LEAD_AGENT_TOOLS surface is
distracting the LLM on simple chat questions (the most likely cause)
and address with prompt tightening before re-attempting.

## Linkage

- HUG-201 (Deep Research umbrella) closes after Phase B lands and CI is green.
- HUG-249's ADR (no new mf_query cache yet) is independent — already shipped.

## Status

- **Phase A (commit 2223f95, 2026-05-16):** audit doc only — no code change. ✓ Shipped.
- **Phase B (this commit, 2026-05-17):** actual deletion + flag flip — user approved walk-through and authorised execution. ✓ Shipped.
- **Migration 019** (drop `research_steps` + `research_findings` tables): **deferred**. The GET endpoints `/plans/{pid}/steps` + `/findings` are still wired in `routes/research.py` because the frontend's `useGetResearchStepsQuery` + `useGetResearchFindingsQuery` haven't migrated to `useGetResearchSubagentCallsQuery` yet (the HUG-245 deferred sub-scope). Tables stay but are inert (no code writes to them); routes return empty arrays. When the frontend hook swap lands, migration 019 follows.

## Phase B diff summary (commit recorded post-push)

- Deleted: 9 production files in `packages/api/src/api/services/research_agent/` (coordinator, executor, executor_parallel, planner, replanner, synthesizer, worker, lead_memory, lead_system_prompt) — ~1380 LOC.
- Deleted: 10 test files (test_research_{coordinator,coordinator_deep,executor,executor_parallel,findings,lead_memory,planner,replanner,synthesizer,worker}.py).
- Deleted: `test_sse_contract.py` + its 2 golden trace files. The lead-path SSE golden trace is a follow-up.
- `routes/research.py`: removed `/approve` route + `expand_plan_into_steps` import + `plan_approved_event` import + `Callable` import + `_decide` helper; renamed `_decide` body to `_transition_to_aborted` inline.
- `routes/threads.py`: removed `route_turn` import + `lead_agent_enabled()` import + the if/else conditional → `stream_lead_turn` is the only path.
- `services/lead_agent.py`: removed the `lead_agent_enabled()` function + the `os`/`_FLAG_ENV` symbols; updated module docstring.
- `tests/test_research_routes.py`: trimmed — kept all `/abort` test cases (renamed from `_approve_` where appropriate), dropped all `/approve` tests. `test_get_plan_steps_returns_list` rewritten to assert empty-list response (legacy expander is gone).
- `tests/test_lead_agent_wiring.py`: removed flag-truthy / flag-falsy parametrized tests since the function no longer exists.
- `CLAUDE.md`: repo-map updated with `lead_agent_prompt.py` + `lead_agent.py` entries; "Key files to read first" section mentions ANCHOR-F.
