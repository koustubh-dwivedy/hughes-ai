"""Reflexion-style numeric verifier (HUG-223, V1).

Opt-in gate that asks a verifier LLM to inspect the synthesized
summary text against the underlying findings' structured rows. If
the summary claims a direction (increase / decrease / "exceeded")
that the data doesn't support, the verifier flags the answer with
a `verifier_warning` annotation.

The verifier does NOT block the answer — it only annotates. The
frontend (HUG-224, V2 audit-trail UI) renders the warning banner
when present. Behind an env flag (`RESEARCH_VERIFIER_ENABLED=1`)
so we can A/B its value before deciding to make it default.

Uses `make_llm(role="verifier")` (HUG-204) so the verifier model
can be tuned independently of the chat/worker LLM.
"""

from __future__ import annotations

import json
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from nl_engine.logging import get_logger
from pydantic import BaseModel

from api.services.research_agent.telemetry import (
    EVENT_VERIFIER_FLAGGED,
    EVENT_VERIFIER_INVOKED,
    log_event,
)
from api.types.research import Finding

_VERIFIER_SYSTEM_PROMPT = """\
You are the VERIFIER AGENT for Hughes AI. Inspect the user-facing
SUMMARY against the underlying FINDINGS rows. Flag the answer ONLY
when the summary makes a numeric or directional claim that the
findings contradict.

Examples of contradictions:
- Summary says "increased YoY" but rows show a decrease.
- Summary cites a number that doesn't appear in any row.
- Summary claims "exceeded threshold X" but no row's metric value
  exceeds X.

Do NOT flag for:
- Qualitative phrasing.
- Rounded vs exact numbers.
- Missing units (the agent's job, not yours).

Return strictly valid JSON:
{
  "flagged": true | false,
  "reason": "<one short sentence; empty when flagged=false>"
}
"""


class VerifierVerdict(BaseModel):
    flagged: bool
    reason: str = ""


_slog = get_logger().bind(component="research.verifier")


def is_enabled() -> bool:
    """Env-flag check. Default off so verifier doesn't fire in
    existing tests or local dev."""
    return os.environ.get("RESEARCH_VERIFIER_ENABLED") == "1"


def _try_parse(raw: str) -> VerifierVerdict | None:
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        raw = "\n".join(lines).strip()
    try:
        obj = json.loads(raw)
        return VerifierVerdict.model_validate(obj)
    except (json.JSONDecodeError, ValueError):
        return None


def _format_input(summary: str, findings: list[Finding]) -> str:
    rows_blob = "\n".join(
        f"- step {str(f.step_id)[:8]}: {f.structured_rows_json or '(no rows)'}"
        for f in findings
    ) or "(no findings)"
    return (
        f"SUMMARY:\n{summary}\n\n"
        f"FINDINGS ROWS:\n{rows_blob}\n\n"
        "Verdict? JSON-only."
    )


def verify(
    summary: str, findings: list[Finding], llm: BaseChatModel,
) -> VerifierVerdict:
    """Ask the verifier LLM. Safe-default to flagged=False on parse
    failure (never block the answer for verifier flakiness)."""
    log_event(EVENT_VERIFIER_INVOKED, summary_chars=len(summary),
              findings_count=len(findings))
    messages = [
        SystemMessage(content=_VERIFIER_SYSTEM_PROMPT),
        HumanMessage(content=_format_input(summary, findings)),
    ]
    response = llm.invoke(messages)
    verdict = _try_parse(str(response.content))
    if verdict is None:
        _slog.warning("verifier.parse_failed")
        return VerifierVerdict(flagged=False, reason="parse_failed")
    if verdict.flagged:
        log_event(
            EVENT_VERIFIER_FLAGGED, reason=verdict.reason[:160],
            summary_chars=len(summary),
        )
    return verdict
