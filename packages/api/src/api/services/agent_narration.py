"""Deterministic narration synthesis for the Thinking-box live trace
(HUG-202 Phase 1).

The ReAct agent's tool-call stream is already structured. We translate
each new message into a single-line, user-facing narration string that
the frontend renders in a rolling Thinking box. Narration is generated
server-side from existing telemetry — no LLM calls — so the line text
is deterministic and assertable from tests.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

# Friendly labels per known tool. Falls through to a generic line for
# anything not in this map.
_TOOL_CALL_LABELS: dict[str, str] = {
    "list_metrics": "Looking up available metrics…",
    "lookup_metric_definition": "Reading the metric definition…",
    "clarify": "Drafting a clarification question…",
    "final_answer": "Drafting your answer…",
}


def _mf_query_call_label(args: dict[str, Any] | None) -> str:
    """Custom narration for `mf_query` so the user sees which metric is
    being looked up rather than a generic "querying metricflow" line."""
    if not isinstance(args, dict):
        return "Querying MetricFlow…"
    metric = args.get("metric")
    if isinstance(metric, str) and metric:
        return f"Querying {metric}…"
    return "Querying MetricFlow…"


def _row_count(result: Any) -> int | None:
    if not isinstance(result, dict):
        return None
    rows = result.get("rows")
    if isinstance(rows, list):
        return len(rows)
    return None


def _list_metrics_count(content: str) -> int | None:
    """`list_metrics` returns a JSON array; count its entries."""
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, list):
        return len(parsed)
    return None


_TOOL_RESULT_LABELS: dict[str, str] = {
    "lookup_metric_definition": "Got the metric definition",
    "final_answer": "Drafting complete",
    "clarify": "Asking for clarification",
}


def _ai_narration(msg: AIMessage) -> str | None:
    if msg.tool_calls:
        first = msg.tool_calls[0]
        name = first.get("name", "")
        if name == "mf_query":
            return _mf_query_call_label(first.get("args"))
        label = _TOOL_CALL_LABELS.get(name)
        if label is not None:
            return label
        return f"Calling {name}…" if name else "Working…"
    if isinstance(msg.content, str) and msg.content.strip():
        return "Reasoning…"
    return None


def _tool_narration(msg: ToolMessage) -> str | None:
    name = msg.name or ""
    content_str = str(msg.content) if msg.content is not None else ""
    try:
        decoded = json.loads(content_str)
    except (json.JSONDecodeError, TypeError):
        decoded = None
    if isinstance(decoded, dict) and "error" in decoded:
        return "Hit an error — adjusting…"
    if name == "list_metrics":
        n = _list_metrics_count(content_str)
        return f"Found {n} metrics" if n is not None else "Got the metric catalog"
    if name == "mf_query":
        n = _row_count(decoded)
        return f"Got {n} rows" if n is not None else "Got results"
    label = _TOOL_RESULT_LABELS.get(name)
    if label is not None:
        return label
    return f"Got result from {name}" if name else "Got results"


def narration_for(msg: Any) -> str | None:
    """Map a graph message to a single Thinking-box line, or None to
    skip narration (system / human / empty AI messages)."""
    if isinstance(msg, AIMessage):
        return _ai_narration(msg)
    if isinstance(msg, ToolMessage):
        return _tool_narration(msg)
    return None
