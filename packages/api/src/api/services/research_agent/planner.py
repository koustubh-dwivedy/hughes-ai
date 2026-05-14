"""Lead planner — depth decision + plan drafting (HUG-208, L1).

The first node of the deep-research coordinator. Given the user's
question + thread history, decides whether to route to the shallow
(existing ReAct) path or to draft a deep research plan. One LLM
call in JSON mode; one retry on schema-validation failure; raises
`PlannerError` if both attempts fail (the coordinator surfaces this
as an error frame).

The plan output schema is fixed and validated by pydantic — the
worker / executor / frontend all consume PlanDraft via this single
contract.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Self

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError, model_validator

from api.services.research_agent.lead_system_prompt import LEAD_SYSTEM_PROMPT
from api.services.research_agent.telemetry import (
    EVENT_PLAN_DRAFT_FAILED,
    EVENT_PLAN_DRAFTED,
    log_event,
)
from api.types.threads import ThreadMessage

# Hard cap on prompt-history characters fed to the planner. A turn
# with a runaway thread history shouldn't blow the lead's context;
# the planner only needs the gist of the conversation so far.
_HISTORY_CHAR_BUDGET = 4000


class PlanStep(BaseModel):
    """One step in a research plan. `dependencies` lists earlier
    ordinals whose findings this step needs."""

    ordinal: int
    description: str
    dependencies: list[int] = Field(default_factory=list)


class PlanDraft(BaseModel):
    """The lead's structured output: the depth decision + (for deep
    turns) the typed plan."""

    route: Literal["shallow", "deep"]
    reason: str
    plan: list[PlanStep] | None = None
    research_question_summary: str

    @model_validator(mode="after")
    def _plan_consistency(self) -> Self:
        if self.route == "deep" and not self.plan:
            raise ValueError("route='deep' requires a non-empty plan list")
        if self.route == "shallow" and self.plan:
            raise ValueError("route='shallow' must have plan=null")
        return self


class PlannerError(RuntimeError):
    """Raised when the planner can't produce a valid PlanDraft after
    one retry. Coordinator catches and surfaces as an SSE error."""


def _summarise_history(history: list[ThreadMessage]) -> str:
    """Compact history into a single text blob the planner can read.
    User + assistant content only; tool noise dropped. Capped at
    `_HISTORY_CHAR_BUDGET` chars to keep the lead's prompt bounded."""
    lines: list[str] = []
    for msg in history:
        if msg.role not in {"user", "assistant"}:
            continue
        body = (msg.content or "").strip()
        if not body:
            continue
        lines.append(f"{msg.role.upper()}: {body}")
    text = "\n".join(lines)
    if len(text) > _HISTORY_CHAR_BUDGET:
        # Keep the *latest* exchanges; the planner cares most about
        # what just happened, not the start of a long thread.
        text = "…(earlier turns elided)…\n" + text[-_HISTORY_CHAR_BUDGET:]
    return text


def _build_user_message(user_question: str, history: list[ThreadMessage]) -> str:
    history_text = _summarise_history(history)
    parts = [f"USER QUESTION: {user_question}"]
    if history_text:
        parts.append(
            "\nPRIOR CONVERSATION "
            "(most recent first is at the bottom):\n"
            f"{history_text}"
        )
    return "\n".join(parts)


def _strip_code_fences(s: str) -> str:
    """Some providers wrap JSON in ```json…``` despite the prompt
    saying not to. Strip the fences before parsing."""
    s = s.strip()
    if s.startswith("```"):
        # Drop the first fence line (```json or ```).
        lines = s.split("\n")
        if lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        s = "\n".join(lines).strip()
    return s


def _try_parse(raw: str) -> PlanDraft:
    """Strict parse-and-validate. Raises ValidationError / ValueError
    /  json.JSONDecodeError if anything's off — caller decides whether
    to retry."""
    cleaned = _strip_code_fences(raw)
    obj = json.loads(cleaned)
    return PlanDraft.model_validate(obj)


def _retry_message(error: str) -> HumanMessage:
    return HumanMessage(
        content=(
            "Your previous response was not valid JSON / did "
            "not match the required schema. Error:\n"
            f"{error}\n\n"
            "Return ONLY the JSON object — no prose, no code "
            "fences. Re-read the rules and try again."
        )
    )


def _emit_success(draft: PlanDraft, attempts: int) -> None:
    log_event(
        EVENT_PLAN_DRAFTED,
        route=draft.route,
        reason=draft.reason[:160],
        plan_size=len(draft.plan) if draft.plan else 0,
        attempts=attempts,
    )


def _fail(exc: Exception, error: str, attempts: int, q_chars: int) -> PlannerError:
    log_event(
        EVENT_PLAN_DRAFT_FAILED,
        attempts=attempts,
        error=error[:300],
        question_chars=q_chars,
    )
    return PlannerError(
        f"planner failed after {attempts} attempts: {error[:300]}"
    )


def draft_plan(
    user_question: str,
    history: list[ThreadMessage],
    llm: BaseChatModel,
) -> PlanDraft:
    """Ask the lead LLM to decide depth + draft a plan. One retry on
    schema failure; on second failure raise PlannerError and emit
    `research.plan.draft_failed`."""
    messages: list[Any] = [
        SystemMessage(content=LEAD_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_message(user_question, history)),
    ]
    last_error: str | None = None
    for attempt in (1, 2):
        response = llm.invoke(messages)
        try:
            draft = _try_parse(str(response.content))
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            if attempt == 1:
                messages.append(response)
                messages.append(_retry_message(last_error))
                continue
            raise _fail(exc, last_error, attempt, len(user_question)) from exc
        _emit_success(draft, attempt)
        return draft
    raise PlannerError(  # pragma: no cover  — loop returns or raises
        f"planner exhausted retries: {last_error}"
    )
