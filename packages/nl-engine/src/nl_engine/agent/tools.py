"""Tool implementations for the ReAct agent.

Each tool has a Pydantic input schema and a typed return shape. The
agent can only call MetricFlow through `mf_query`; there is no
free-form SQL escape hatch in steady state (ADR-0003 #3). The
`final_answer` tool is the single terminal: every successful turn ends
with the orchestrator extracting its payload.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from nl_engine.agent.memory_tools import (  # noqa: F401  # re-export
    LEAD_AGENT_MEMORY_TOOLS,
    read_memory,
    write_memory,
)
from nl_engine.agent.mf_query_runner import (
    run_mf_query_with_retry,
    safe_mf,
)
from nl_engine.agent.plan_tool import (  # noqa: F401  # re-export
    PlanStepDescriptor,
    propose_plan,
)
from nl_engine.agent.state import ClarifyResult, FinalAnswer
from nl_engine.agent.subagent_tool import run_subagent  # noqa: F401  # re-export
from nl_engine.logging import get_logger

slog = get_logger().bind(component="agent.tools")


class MetricSummary(BaseModel):
    name: str
    dimensions: list[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    name: str
    dimensions: list[str]
    description: str | None = None


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
    mf = safe_mf()
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
    mf = safe_mf()
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
            " TIME-RANGE FILTERS: for a date range that covers a whole"
            " month or quarter, use an EXCLUSIVE upper bound on the"
            " NEXT period's start, NOT an inclusive bound on the last"
            " day. MetricFlow compares against the underlying timestamp"
            " even for month-grain dims, so `<= '2026-03-01'` only"
            " catches rows on March 1, NOT the rest of March."
            " For Q1 2026 (Jan-Mar inclusive), write:"
            " \"{{ Dimension('metric_time__month') }} >= '2026-01-01' AND"
            " {{ Dimension('metric_time__month') }} < '2026-04-01'\"."
            " For \"latest month\" filters, use `= '2026-04-01'`"
            " (equality, on the month-start date)."
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
    return run_mf_query_with_retry(args)


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

    `rows`, `mf_query`, and `summary` MUST be self-consistent — all
    three describe the SAME answer:

    - If your `summary` states a single number (e.g., "the Q1 average
      was $92,665"), `rows` must contain exactly that single matching
      row.
    - If your `summary` describes a breakdown across N items, `rows`
      must contain those N rows in matching shape.
    - `mf_query` must echo the exact arguments of the call that
      produced `rows`.

    If you made multiple `mf_query` calls during this turn — for
    example a probe to find the latest month, then a refined query you
    intend as the actual answer — consciously pick which single call
    is your answer, then populate `rows` and `mf_query` from THAT call
    only. Never carry rows from an earlier exploratory query you
    replaced. Never mix rows from one call with `mf_query` arguments
    from another. Re-read your own `summary` before submitting; if the
    numbers in `rows` don't reproduce the claim you made in `summary`,
    fix one or the other before issuing `final_answer`.

    The `rows` you submit MUST be the LITERAL rows MetricFlow returned
    in your chosen `mf_query` call — same column names, same values,
    same shape, no transformations. Do NOT post-process: do not rename
    columns to make them more descriptive (e.g. inventing
    `30_plus_past_due_loan_count` instead of the literal MF column
    `past_due_loan_count`), do not aggregate the rows client-side
    (e.g. summing per-bucket counts into a single total), do not drop
    or add columns. If you need a different aggregation, filter, or
    grain, issue a NEW `mf_query` with the right arguments — let
    MetricFlow do the work, then echo its result verbatim into `rows`.
    The grader expects the column names produced by MetricFlow, not
    your relabeled versions.
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


# Chat agent uses ALL_TOOLS; lead agent uses LEAD_AGENT_TOOLS. Lead omits
# mf_query + lookup_metric_definition so it must delegate via run_subagent.
ALL_TOOLS = [list_metrics, lookup_metric_definition, mf_query, clarify, final_answer]
LEAD_AGENT_TOOLS = [list_metrics, clarify, final_answer, *LEAD_AGENT_MEMORY_TOOLS,
                    propose_plan, run_subagent]


def serialize_tool_result(value: Any) -> str:
    """Stringify a tool return value for the LangChain ToolMessage. The
    LLM sees this verbatim, so we keep it compact JSON."""
    return json.dumps(value, default=str)
