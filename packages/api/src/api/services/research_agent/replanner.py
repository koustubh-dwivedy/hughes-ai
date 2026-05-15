"""Re-plan logic (HUG-221, M2).

When findings reveal that the current plan can't fulfill the user's
question (e.g. "branch X has no Q3 data, can't fulfill step 4"), the
lead writes a new plan version. This module exposes the decision +
persistence primitives:

  - `decide_revise(plan, findings, lead_note, llm)` → ReviseDecision
      Asks the lead LLM whether the current findings + notes
      warrant a new plan. Strict JSON output; one retry on parse
      failure; never raises (returns revise=False as the safe fallback).

  - `revise_plan(plan, new_draft, db_url)` → Plan
      Persists the new plan version (status='approved'), transitions
      the previous plan to 'superseded', emits the
      `research.plan.revised` event payload (caller yields).

Hard cap: `MAX_PLAN_VERSIONS=5` per the risk-mitigation note in the
session plan. A 6th revise call short-circuits and logs
`research.plan.replan_capped` instead of recursing forever.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from nl_engine.logging import get_logger
from pydantic import BaseModel

from api.prometheus import research_plan_versions_total
from api.repo import research as research_repo
from api.services.research_agent.events import plan_revised_event
from api.services.research_agent.telemetry import (
    EVENT_PLAN_REVISED,
    log_event,
)
from api.types.research import Finding, Plan

_MAX_PLAN_VERSIONS = 5

_REPLAN_SYSTEM_PROMPT = """\
You are the LEAD AGENT for Hughes AI. A research plan has already
run; you now have findings from worker subagents. Decide whether the
plan needs revising.

REVISE when:
- A finding reveals the originally-planned data isn't available
  (e.g. metric undefined for the requested time window).
- A finding contradicts the plan's assumptions (e.g. expected
  high-volume segment is actually empty).
- A finding suggests a more focused decomposition would yield a
  better answer.

DO NOT REVISE when:
- All findings are consistent with the plan.
- The plan is just slow; patience isn't a reason to re-plan.

Return strictly valid JSON:

{
  "revise": true | false,
  "reason": "<one short sentence>",
  "new_plan": null | [
    {"ordinal": 1, "description": "...", "dependencies": []},
    ...
  ]
}

`new_plan` MUST be null when `revise` is false, and a non-empty list
when revise is true.
"""


class ReviseDecision(BaseModel):
    revise: bool
    reason: str
    new_plan: list[dict[str, Any]] | None = None


_slog = get_logger().bind(component="research.replanner")


def _try_parse(raw: str) -> ReviseDecision:
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        raw = "\n".join(lines).strip()
    return ReviseDecision.model_validate(json.loads(raw))


def _format_input(
    plan: Plan, findings: list[Finding], lead_note: str,
) -> str:
    findings_blob = "\n\n".join(
        f"- {f.summary_text or '(no summary)'}"
        + (f"\n  rows: {f.structured_rows_json[:3]}…"
           if f.structured_rows_json else "")
        for f in findings
    ) or "(none)"
    note_blob = lead_note or "(no notes yet)"
    return (
        f"CURRENT PLAN (v{plan.version}):\n"
        f"{json.dumps(plan.plan_json.get('plan'), indent=2)}\n\n"
        f"FINDINGS SO FAR:\n{findings_blob}\n\n"
        f"LEAD NOTES:\n{note_blob}\n\n"
        "Should we revise the plan? Respond JSON-only."
    )


def decide_revise(
    plan: Plan, findings: list[Finding], lead_note: str,
    llm: BaseChatModel,
) -> ReviseDecision:
    """Ask the lead LLM whether to revise. Never raises; on parse
    failure, returns revise=False with the parse error in reason."""
    messages = [
        SystemMessage(content=_REPLAN_SYSTEM_PROMPT),
        HumanMessage(content=_format_input(plan, findings, lead_note)),
    ]
    for _attempt in (1, 2):
        try:
            return _try_parse(str(llm.invoke(messages).content))
        except (json.JSONDecodeError, ValueError):
            continue
    _slog.warning(
        "replanner.parse_failed", plan_id=str(plan.plan_id),
    )
    return ReviseDecision(
        revise=False, reason="parse_failed (default to no revise)",
    )


def revise_plan(
    *, plan: Plan, decision: ReviseDecision, db_url: str,
) -> Plan | None:
    """Persist a new plan version with the revised plan_json.
    Returns the new plan or None if the cap is hit / decision says
    not to revise."""
    if not decision.revise or decision.new_plan is None:
        return None
    if plan.version >= _MAX_PLAN_VERSIONS:
        log_event(
            "research.plan.replan_capped",
            plan_id=str(plan.plan_id), version=plan.version,
            max_versions=_MAX_PLAN_VERSIONS,
        )
        _slog.warning(
            "replanner.cap_hit", plan_id=str(plan.plan_id),
            version=plan.version,
        )
        return None
    # Build PlanDraft-shaped JSON for the new plan.
    new_plan_json = dict(plan.plan_json)
    new_plan_json["plan"] = decision.new_plan
    new_plan_json["reason"] = decision.reason
    # Persist new version with status='approved' — revisions inherit
    # the original user approval (HUG-221 spec).
    new_plan = research_repo.create_plan(
        thread_id=plan.thread_id, plan_json=new_plan_json,
        db_url=db_url, status="approved",
    )
    research_repo.update_plan_status(plan.plan_id, "superseded", db_url)
    research_plan_versions_total.inc()
    log_event(
        EVENT_PLAN_REVISED, plan_id=str(new_plan.plan_id),
        old_plan_id=str(plan.plan_id),
        old_version=plan.version, new_version=new_plan.version,
        reason=decision.reason[:160],
    )
    return new_plan


def revise_plan_event(plan: Plan, *, prior_version: int) -> dict[str, Any]:
    """SSE event payload signaling the frontend that a new plan
    version exists. Frontend invalidates the ResearchPlan tag."""
    return plan_revised_event(plan, prior_version=prior_version)
