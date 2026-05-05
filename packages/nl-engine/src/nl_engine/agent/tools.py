"""Tool implementations for the ReAct agent.

Each tool has a Pydantic input schema and a typed return shape. The
agent can only call MetricFlow through `mf_query`; there is no
free-form SQL escape hatch in steady state (ADR-0003 #3). The
`final_answer` tool is the single terminal: every successful turn ends
with the orchestrator extracting its payload.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from nl_engine.agent.state import ClarifyResult, FinalAnswer

log = logging.getLogger(__name__)

# How many times mf_query is allowed to retry against a model-corrected
# argument set before we surface the failure to the agent. Two retries
# matches the plan's "max-2 internal retry" decision.
_MF_QUERY_MAX_RETRIES = 2


class MetricSummary(BaseModel):
    name: str
    dimensions: list[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    name: str
    dimensions: list[str]
    description: str | None = None


def _safe_mf() -> Any:
    """Import MetricFlow lazily so unit tests don't require dbt deps."""
    from nl_engine.repo import metricflow as mf

    return mf


@tool
def list_metrics() -> list[dict[str, Any]]:
    """Return every metric MetricFlow knows about + the dimensions it
    supports. Cache-eligible (the catalog only changes on a deploy)."""
    mf = _safe_mf()
    return [
        MetricSummary(name=m.name, dimensions=m.dimensions).model_dump()
        for m in mf.list_metrics()
    ]


@tool
def lookup_metric_definition(name: str) -> dict[str, Any]:
    """Return the dimension list + (eventually) prose definition for a
    single metric. Useful when the agent wants to confirm a measure
    is what the user is asking about before issuing a query."""
    mf = _safe_mf()
    for m in mf.list_metrics():
        if m.name == name:
            return MetricDefinition(name=m.name, dimensions=m.dimensions).model_dump()
    raise ValueError(f"unknown metric: {name}")


class MfQueryArgs(BaseModel):
    """The structured arguments the agent must produce to call MetricFlow."""

    metric: str
    dimensions: list[str] = Field(default_factory=list)
    where: str | None = None
    order: str | None = None
    limit: int = 100


def _mf_query_once(args: MfQueryArgs) -> dict[str, Any]:
    mf = _safe_mf()
    result = mf.query(
        metric=args.metric,
        dimensions=args.dimensions or None,
        where=args.where,
        order=args.order,
        limit=args.limit,
    )
    return {
        "metric": result.metric,
        "dimensions": result.dimensions,
        "rows": result.rows,
    }


@tool
def mf_query(
    metric: str,
    dimensions: list[str] | None = None,
    where: str | None = None,
    order: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Run a MetricFlow query. Retries up to twice on transient errors
    so the agent doesn't waste a step-cap slot fighting a flaky query.
    """
    args = MfQueryArgs(
        metric=metric,
        dimensions=dimensions or [],
        where=where,
        order=order,
        limit=limit,
    )
    last_error: Exception | None = None
    for attempt in range(_MF_QUERY_MAX_RETRIES + 1):
        try:
            return _mf_query_once(args)
        except Exception as exc:
            last_error = exc
            log.warning("mf_query attempt %s failed: %s", attempt + 1, exc)
    raise RuntimeError(f"mf_query failed after retries: {last_error}")


@tool
def clarify(question: str, options: list[str] | None = None) -> dict[str, Any]:
    """Terminate the turn with a clarification question for the user.

    The agent calls this when the request is genuinely ambiguous
    (multiple valid interpretations) instead of guessing.
    """
    result = ClarifyResult(question=question, options=options or [])
    return result.model_dump()


@tool
def final_answer(
    summary: str,
    openui_dsl: str | None = None,
    rows: list[dict[str, Any]] | None = None,
    mf_query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single typed terminal for every successful turn.

    Populate `openui_dsl` with valid OpenUI Lang DSL whenever a chart,
    table, KPI tile, or stack of widgets would communicate the answer
    better than prose alone. The system prompt lists every component
    you may use — stay strictly within that registered library, and
    follow the openui-lang syntax rules verbatim (every variable must
    be reachable from `root`, positional args only, no colon syntax).

    Leave `openui_dsl` as None for purely textual answers (a one-line
    definition, a short qualitative summary). `summary` is shown in
    every case; `openui_dsl` augments it.

    `rows` and `mf_query` should be populated for any answer that
    touched MetricFlow, regardless of whether you emit DSL.
    """
    payload = FinalAnswer(
        summary=summary,
        openui_dsl=openui_dsl,
        rows=rows,
        mf_query=mf_query,
    )
    return payload.model_dump()


# Registered tool list — the order matches the prompt template so the
# LLM sees them in dependency order (catalog lookups before query, query
# before final_answer).
ALL_TOOLS = [
    list_metrics,
    lookup_metric_definition,
    mf_query,
    clarify,
    final_answer,
]


def serialize_tool_result(value: Any) -> str:
    """Stringify a tool return value for the LangChain ToolMessage. The
    LLM sees this verbatim, so we keep it compact JSON."""
    return json.dumps(value, default=str)
