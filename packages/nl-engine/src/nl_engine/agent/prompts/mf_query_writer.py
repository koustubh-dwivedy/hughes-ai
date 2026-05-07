"""DSPy module: produce a MetricFlow query JSON from a user question.

Output mirrors the agent's `mf_query` tool args: metric, dimensions,
where, order, limit. Every column string MUST be drawn verbatim from
the catalog the agent passed in.
"""

from __future__ import annotations

import dspy


class MetricFlowQuerySignature(dspy.Signature):
    """Translate a user's question into MetricFlow query arguments.

    Rules:
      * `metric` MUST be one of the metric names in `metric_catalog`.
      * `dimensions` MUST be drawn verbatim from that metric's catalog
        dimension list (e.g., `deposits_monthly_grain__branch`,
        `metric_time__month`). NEVER paraphrase to user-friendly names.
      * `where` uses Jinja Dimension() wrappers, e.g.
        "{{ Dimension('metric_time__day') }} >= '2026-01-01'".
      * `order` is a bare column for ASC, `-` prefix for DESC. Never
        emit the words "ASC" or "DESC". The order column must already
        be in `dimensions` or be the metric name itself.
      * `limit` defaults to 100; lower to 1 for "what's the X" asks.
    """

    question: str = dspy.InputField(desc="The latest user message.")
    metric_catalog: str = dspy.InputField(
        desc=(
            "JSON array of {name, dimensions} entries — the literal "
            "catalog returned by `list_metrics()`."
        ),
    )
    conversation_history: str = dspy.InputField(
        desc="Prior turns for context (oldest first).", default=""
    )
    rationale: str = dspy.OutputField(
        desc="One sentence on why this metric + filter combo answers the question."
    )
    metric: str = dspy.OutputField(desc="The metric name (verbatim from the catalog).")
    dimensions: str = dspy.OutputField(
        desc="JSON array of dimension strings (verbatim from the catalog), or '[]'."
    )
    where: str = dspy.OutputField(
        desc="MetricFlow `where` predicate, or empty string."
    )
    order: str = dspy.OutputField(
        desc="Order-by column (bare = ASC, `-` prefix = DESC), or empty string."
    )
    limit: int = dspy.OutputField(desc="Row limit. 100 default; 1 for single-value.")


class MetricFlowQueryWriter(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(MetricFlowQuerySignature)

    def forward(
        self,
        question: str,
        metric_catalog: str,
        conversation_history: str = "",
    ) -> dspy.Prediction:
        return self.predict(
            question=question,
            metric_catalog=metric_catalog,
            conversation_history=conversation_history,
        )
