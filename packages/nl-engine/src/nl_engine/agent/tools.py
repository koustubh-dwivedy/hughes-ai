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
import time
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from nl_engine.agent.mf_errors import classify_mf_error, extract_mf_hint
from nl_engine.agent.state import ClarifyResult, FinalAnswer

log = logging.getLogger(__name__)

# Transient errors get one extra retry; structural errors are surfaced
# to the agent immediately so it can correct on the next LLM call
# (HUG-190 Phase B).
_MF_QUERY_TRANSIENT_RETRY_DELAY_S = 0.5


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
    """Return every metric MetricFlow knows about plus the EXACT dimension
    strings that metric supports. Call this FIRST before any `mf_query`.

    The dimension strings returned here are the literal bytes you must
    pass to `mf_query`. Examples of valid dimensions look like
    `deposits_monthly_grain__branch`, `application__channel`,
    `metric_time__month`. Do NOT paraphrase them into user-friendly
    names like `branch` or `branch_name`; MetricFlow rejects anything
    that isn't an exact match.

    Cache-eligible (the catalog only changes on a deploy).
    """
    mf = _safe_mf()
    return [
        MetricSummary(name=m.name, dimensions=m.dimensions).model_dump()
        for m in mf.list_metrics()
    ]


@tool
def lookup_metric_definition(name: str) -> dict[str, Any]:
    """Return the dimension list for a single metric. Most of the time
    `list_metrics()` already gives you everything you need; reach for
    this only when you need to confirm a single metric's dimensions in
    isolation (e.g., the user asked about a specific metric by name and
    you want to validate it exists before issuing a query).

    Returns the same dimension shape as `list_metrics()` — the strings
    are the literal bytes to pass to `mf_query`.
    """
    mf = _safe_mf()
    for m in mf.list_metrics():
        if m.name == name:
            return MetricDefinition(name=m.name, dimensions=m.dimensions).model_dump()
    raise ValueError(f"unknown metric: {name}")


class MfQueryArgs(BaseModel):
    """The structured arguments the agent must produce to call MetricFlow.

    Every field's value must be drawn from what `list_metrics()` returns —
    do NOT invent column names or paraphrase user terms.
    """

    metric: str = Field(
        description=(
            "Exact metric name from `list_metrics()` (e.g.,"
            " 'loan_to_deposit_ratio', 'deposits_by_branch'). Case-sensitive."
        ),
    )
    dimensions: list[str] = Field(
        default_factory=list,
        description=(
            "Group-by columns. Each string MUST be one of the dimensions"
            " returned by `list_metrics()` for this metric — copy them"
            " verbatim. Use `metric_time__month` for monthly time series,"
            " `metric_time__day` for daily, etc. Examples of valid values:"
            " 'deposits_monthly_grain__branch', 'application__channel'."
            " NEVER paraphrase to user-friendly names like 'branch' or"
            " 'branch_name'."
        ),
    )
    where: str | None = Field(
        default=None,
        description=(
            "Filter predicate. MetricFlow requires Jinja-templated"
            " `Dimension()` wrappers; bare columns are rejected."
            " Format: \"{{ Dimension('<column_name>') }} <op> '<value>'\"."
            " Examples (the literal {{ }} braces are required):"
            " \"{{ Dimension('deposits_monthly_grain__as_of_month') }} = '2026-04-01'\","  # noqa: E501
            " \"{{ Dimension('application__channel') }} = 'online'\","
            " \"{{ Dimension('metric_time__day') }} >= '2026-01-01'\"."
            " Multiple conditions: chain with AND inside one string."
            " <column_name> must be a dimension in `list_metrics()`."
        ),
    )
    order: str | None = Field(
        default=None,
        description=(
            "Order-by column. JUST the column name — bare for ASC, with"
            " a `-` prefix for DESC. NEVER use the words ASC or DESC;"
            " MetricFlow rejects them outright."
            " Examples: 'metric_time__month' (ASC), '-metric_time__month'"
            " (DESC), '-loan_to_deposit_ratio' (DESC by metric value)."
            " Multi-key: comma-separated, e.g.,"
            " 'metric_time__month,-revenue'."
            " The column must already appear in `dimensions` or be the"
            " metric name itself; otherwise MetricFlow rejects with"
            " 'does not match exactly one of the query items'."
        ),
    )
    limit: int = Field(
        default=100,
        description=(
            "Row limit. Default 100 is fine for most queries. Raise only"
            " when the user explicitly asks for more or when summing all"
            " rows requires it. Lower (e.g., 1) when the user asks 'what"
            " is X this month' — a single value is enough."
        ),
    )


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
    """Run a MetricFlow query and return the resulting rows.

    Workflow: call `list_metrics()` first to see the exact metric and
    dimension strings; pass those strings VERBATIM. Do NOT paraphrase
    user-friendly terms ('branch', 'this month', 'by product') into
    column names — use the exact semantic IDs the catalog returned
    (e.g., 'deposits_monthly_grain__branch', 'metric_time__month').

    Order-by syntax: pass JUST the column name. Bare = ascending;
    `-`-prefix = descending. NEVER use the words 'ASC' or 'DESC' —
    MetricFlow rejects them. Examples:
      order='metric_time__month'       (ASC)
      order='-metric_time__month'      (DESC)
      order='-loan_to_deposit_ratio'   (DESC by metric value)
    The order column must already be in `dimensions` or be the metric
    name. Otherwise MetricFlow returns 'does not match exactly one of
    the query items'.

    On error: read the MetricFlow error message — it usually includes
    a 'did you mean: [...]' suggestion list. Adjust your arguments
    based on that list rather than retrying identical args.
    """
    args = MfQueryArgs(
        metric=metric,
        dimensions=dimensions or [],
        where=where,
        order=order,
        limit=limit,
    )
    return _run_mf_query_with_retry(args)


def _run_mf_query_with_retry(args: MfQueryArgs) -> dict[str, Any]:
    """Smart retry: surface structural errors immediately; retry only
    transient errors once with a small backoff (HUG-190 Phase B)."""
    try:
        return _mf_query_once(args)
    except Exception as exc:  # noqa: BLE001 — surfaced as tool-result
        kind = classify_mf_error(exc)
        log.warning("mf_query attempt 1 failed (%s): %s", kind, exc)
        if kind != "transient":
            return _mf_error_payload(exc)
    time.sleep(_MF_QUERY_TRANSIENT_RETRY_DELAY_S)
    try:
        return _mf_query_once(args)
    except Exception as retry_exc:  # noqa: BLE001 — surfaced as tool-result
        log.warning("mf_query attempt 2 failed (transient retry): %s", retry_exc)
        return _mf_error_payload(retry_exc)


def _mf_error_payload(exc: Exception) -> dict[str, Any]:
    """Return a structured tool-result so the agent sees the error +
    any 'did you mean' hint MetricFlow surfaced. The graph's tool
    executor wraps tool returns in a ToolMessage; the agent reads this
    on the next step."""
    msg = str(exc)
    hint = extract_mf_hint(msg)
    payload: dict[str, Any] = {"error": msg}
    if hint:
        payload["hint"] = hint
    return payload


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
