"""Tests for HUG-261 — error_kind classifier + lead retry-policy prompt."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from nl_engine.agent.lead_agent_prompt import LEAD_AGENT_SYSTEM_PROMPT
from nl_engine.agent.subagent_failure import (
    ERROR_KIND_STRUCTURAL_STEP_CAP,
    ERROR_KIND_TRANSIENT_WORKER_EXCEPTION,
    ERROR_KIND_UNKNOWN,
    classify_no_final_answer,
)


def test_classify_step_cap_message_returns_structural() -> None:
    """The AIMessage emitted by graph._step_cap_node should classify as
    structural_step_cap — the only kind the lead is told NOT to retry
    identically."""
    step_cap_msg = AIMessage(
        content="I couldn't reach an answer within the 10-step limit for "
        "this turn. Try rephrasing or breaking the question into smaller "
        "parts."
    )
    assert (
        classify_no_final_answer([HumanMessage(content="q"), step_cap_msg])
        == ERROR_KIND_STRUCTURAL_STEP_CAP
    )


def test_classify_other_ai_message_returns_unknown() -> None:
    other = AIMessage(content="I'm done now without a tool call.")
    assert (
        classify_no_final_answer([HumanMessage(content="q"), other])
        == ERROR_KIND_UNKNOWN
    )


def test_classify_no_messages_returns_unknown() -> None:
    assert classify_no_final_answer([]) == ERROR_KIND_UNKNOWN


def test_finalize_batch_emits_structural_step_cap_kind() -> None:
    """When the worker's terminal AIMessage is the step-cap message,
    _finalize_batch should return error_kind=structural_step_cap."""
    from nl_engine.agent import subagent_tool as st

    step_cap_msg = AIMessage(
        content="I couldn't reach an answer within the 10-step limit for "
        "this turn."
    )
    raw = [
        {
            "call_id": "11111111-1111-1111-1111-111111111111",
            "final": None,
            "messages": [HumanMessage(content="q"), step_cap_msg],
            "exc": None,
        }
    ]
    captured: dict[str, Any] = {}
    real_record = st._record_failure
    st._record_failure = (  # type: ignore[assignment]
        lambda cid, db, err, kind: (
            captured.__setitem__("error_kind", kind)
            or {"error": err, "error_kind": kind, "call_id": str(cid)}
        )
    )
    try:
        out = st._finalize_batch(raw, thread_id=uuid4(), db_url="x")
    finally:
        st._record_failure = real_record  # type: ignore[assignment]

    assert out[0]["error_kind"] == ERROR_KIND_STRUCTURAL_STEP_CAP
    assert captured["error_kind"] == ERROR_KIND_STRUCTURAL_STEP_CAP


def test_finalize_batch_emits_transient_kind_on_exception() -> None:
    """Python exception in worker → transient_worker_exception kind."""
    from nl_engine.agent import subagent_tool as st

    raw = [
        {
            "call_id": "22222222-2222-2222-2222-222222222222",
            "final": None,
            "messages": [],
            "exc": RuntimeError("mf CLI crashed"),
        }
    ]
    real_record = st._record_failure
    st._record_failure = (  # type: ignore[assignment]
        lambda cid, db, err, kind: {
            "error": err, "error_kind": kind, "call_id": str(cid),
        }
    )
    try:
        out = st._finalize_batch(raw, thread_id=uuid4(), db_url="x")
    finally:
        st._record_failure = real_record  # type: ignore[assignment]

    assert out[0]["error_kind"] == ERROR_KIND_TRANSIENT_WORKER_EXCEPTION


def test_lead_prompt_includes_retry_policy_rules() -> None:
    """The lead's system prompt must teach the lead how to handle
    error_kind values — without this, retry behavior is pure LLM judgment."""
    p = LEAD_AGENT_SYSTEM_PROMPT
    assert "Handling subagent failures" in p
    assert "structural_step_cap" in p
    assert "transient_worker_exception" in p
    assert "NEVER retry the same prompt more than once" in p
    assert "NEVER silently drop a failed sub-question" in p
