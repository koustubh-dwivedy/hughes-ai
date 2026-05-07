"""HUG-202 Phase 1: deterministic narration synthesis from agent
messages. The Thinking-box copy is generated server-side from existing
tool events so tests can assert exact strings."""

from __future__ import annotations

import json

from api.services.agent_narration import narration_for
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def _ai_with_tool(name: str, args: dict[str, object] | None = None) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args or {}, "id": "c"}],
    )


def test_human_message_has_no_narration() -> None:
    assert narration_for(HumanMessage(content="hi")) is None


def test_system_message_has_no_narration() -> None:
    assert narration_for(SystemMessage(content="sys")) is None


def test_ai_with_no_content_and_no_tool_calls_has_no_narration() -> None:
    assert narration_for(AIMessage(content="")) is None


def test_list_metrics_call_label() -> None:
    assert narration_for(_ai_with_tool("list_metrics")) == (
        "Looking up available metrics…"
    )


def test_lookup_metric_definition_call_label() -> None:
    assert narration_for(_ai_with_tool("lookup_metric_definition")) == (
        "Reading the metric definition…"
    )


def test_mf_query_call_uses_metric_name_when_present() -> None:
    msg = _ai_with_tool("mf_query", {"metric": "loan_to_deposit_ratio"})
    assert narration_for(msg) == "Querying loan_to_deposit_ratio…"


def test_mf_query_call_falls_back_when_metric_absent() -> None:
    msg = _ai_with_tool("mf_query", {})
    assert narration_for(msg) == "Querying MetricFlow…"


def test_final_answer_call_label() -> None:
    assert narration_for(_ai_with_tool("final_answer")) == "Drafting your answer…"


def test_clarify_call_label() -> None:
    assert narration_for(_ai_with_tool("clarify")) == (
        "Drafting a clarification question…"
    )


def test_unknown_tool_falls_through_to_generic_label() -> None:
    assert narration_for(_ai_with_tool("future_tool")) == "Calling future_tool…"


def test_list_metrics_result_counts_entries() -> None:
    result = json.dumps([{"name": "m1"}, {"name": "m2"}, {"name": "m3"}])
    msg = ToolMessage(content=result, name="list_metrics", tool_call_id="c")
    assert narration_for(msg) == "Found 3 metrics"


def test_mf_query_result_counts_rows() -> None:
    result = json.dumps({"metric": "x", "dimensions": [], "rows": [{"a": 1}]})
    msg = ToolMessage(content=result, name="mf_query", tool_call_id="c")
    assert narration_for(msg) == "Got 1 rows"


def test_tool_error_payload_surfaces_recovery_line() -> None:
    result = json.dumps({"error": "no such column", "hint": "did you mean..."})
    msg = ToolMessage(content=result, name="mf_query", tool_call_id="c")
    assert narration_for(msg) == "Hit an error — adjusting…"


def test_final_answer_result_label() -> None:
    msg = ToolMessage(
        content=json.dumps({"summary": "x"}),
        name="final_answer",
        tool_call_id="c",
    )
    assert narration_for(msg) == "Drafting complete"


def test_unknown_tool_result_falls_through() -> None:
    msg = ToolMessage(content="{}", name="future_tool", tool_call_id="c")
    assert narration_for(msg) == "Got result from future_tool"
