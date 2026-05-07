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
from nl_engine.logging import get_logger

log = logging.getLogger(__name__)
slog = get_logger().bind(component="agent.tools")

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
    """Return the dimension list for a single metric — use only to
    confirm a specific metric exists when `list_metrics()` isn't
    enough. Same dimension format as `list_metrics()`.
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
            "Group-by columns — copy verbatim from `list_metrics()`."
            " e.g. 'deposits_monthly_grain__branch', 'metric_time__month'."
            " NEVER paraphrase ('branch', 'branch_name')."
        ),
    )
    where: str | None = Field(
        default=None,
        description=(
            "Filter predicate. MetricFlow requires Jinja-templated"
            " `Dimension()` wrappers; bare columns are rejected."
            " Format: \"{{ Dimension('<column>') }} <op> '<value>'\"."
            " Example: \"{{ Dimension('metric_time__day') }} >= '2026-01-01'\"."
            " Chain conditions with AND. <column> must be in `list_metrics()`."
        ),
    )
    order: str | None = Field(
        default=None,
        description=(
            "Order-by column. JUST the column name — bare for ASC, `-`"
            " prefix for DESC. NEVER use the words ASC or DESC."
            " Examples: 'metric_time__month', '-loan_to_deposit_ratio'."
            " Column must appear in `dimensions` or be the metric name."
        ),
    )
    limit: int = Field(
        default=100,
        description="Row limit. Default 100. Lower to 1 for single-value asks.",
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

    Workflow: call `list_metrics()` first; pass dimension strings VERBATIM.
    NEVER paraphrase user terms — use the catalog's semantic IDs (e.g.,
    'deposits_monthly_grain__branch', 'metric_time__month').

    Order: bare column = ASC, `-` prefix = DESC. Never use the words
    'ASC' or 'DESC' — MetricFlow rejects them. The order column must
    already be in `dimensions` or be the metric name.

    On error: READ the MetricFlow message — it usually has a 'did you
    mean: [...]' hint. Use it instead of retrying identical args.
    """
    args = MfQueryArgs(
        metric=metric,
        dimensions=dimensions or [],
        where=where,
        order=order,
        limit=limit,
    )
    return _run_mf_query_with_retry(args)


def _log_mf_run(
    args: MfQueryArgs, result: dict[str, Any], t0: float, attempt: int
) -> None:
    slog.info(
        "mf_query.run",
        metric=args.metric,
        dimensions=list(args.dimensions),
        where=args.where,
        order=args.order,
        limit=args.limit,
        row_count=len(result.get("rows", [])),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
        attempt=attempt,
    )


def _run_mf_query_with_retry(args: MfQueryArgs) -> dict[str, Any]:
    """Smart retry: surface structural errors immediately; retry only
    transient errors once with a small backoff (HUG-190 Phase B)."""
    t0 = time.monotonic()
    try:
        result = _mf_query_once(args)
        _log_mf_run(args, result, t0, attempt=1)
        return result
    except Exception as exc:  # noqa: BLE001 — surfaced as tool-result
        kind = classify_mf_error(exc)
        slog.warning(
            "mf_query.attempt_failed",
            metric=args.metric, attempt=1, kind=kind, error=str(exc)[:300],
        )
        log.warning("mf_query attempt 1 failed (%s): %s", kind, exc)
        if kind != "transient":
            return _mf_error_payload(exc)
    time.sleep(_MF_QUERY_TRANSIENT_RETRY_DELAY_S)
    try:
        result = _mf_query_once(args)
        _log_mf_run(args, result, t0, attempt=2)
        return result
    except Exception as retry_exc:  # noqa: BLE001 — surfaced as tool-result
        slog.warning(
            "mf_query.attempt_failed",
            metric=args.metric, attempt=2,
            kind="transient_retry_failed", error=str(retry_exc)[:300],
        )
        log.warning("mf_query attempt 2 failed (transient retry): %s", retry_exc)
        return _mf_error_payload(retry_exc)


def _mf_error_payload(exc: Exception) -> dict[str, Any]:
    """Structured tool-result so the agent sees the error + any 'did
    you mean' hint MetricFlow surfaced (read on the next step)."""
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

    Populate `openui_dsl` (valid OpenUI Lang DSL — see system prompt
    for the registered components) when a chart/table/KPI communicates
    the answer better than prose. None for purely textual answers.
    `rows` + `mf_query` should be populated for any answer that
    touched MetricFlow, regardless of whether DSL is emitted.
    """
    payload = FinalAnswer(
        summary=summary,
        openui_dsl=openui_dsl,
        rows=rows,
        mf_query=mf_query,
    )
    slog.info(
        "agent.final_answer",
        summary_len=len(summary or ""),
        has_dsl=bool(openui_dsl),
        row_count=len(rows or []),
        has_mf_query=mf_query is not None,
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
