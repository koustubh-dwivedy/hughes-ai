"""DSPy module: pick (or skip) a chart spec for a finished MF query.

Output is a small JSON envelope describing a chart: `{type, x, y}` for
line/bar; `{type: "kpi", value}` for a single-value answer; or empty
string when prose is enough.
"""

from __future__ import annotations

import dspy


class RenderChartSpecSignature(dspy.Signature):
    """Choose the most communicative visualization for a result set.

    Rules:
      * Single-value answer (1 row, 1 metric column): emit `kpi`.
      * Time series (rows ordered by metric_time__*): emit `line`.
      * Categorical breakdown with ≤10 rows: emit `bar`.
      * Otherwise leave `chart_spec` empty so the answer renders as
        prose only.

    `chart_spec` is a JSON object the agent will hand to OpenUI; an
    empty string means "no chart, prose only".
    """

    rows: str = dspy.InputField(
        desc="JSON array of MetricFlow result rows (each a flat dict)."
    )
    intent: str = dspy.InputField(
        desc="The user's question, so the chart matches what was asked."
    )
    rationale: str = dspy.OutputField(
        desc="One sentence on why this chart type (or prose-only) was chosen."
    )
    chart_spec: str = dspy.OutputField(
        desc=(
            'JSON: {type:"line"|"bar"|"kpi", x:..., y:...} '
            'OR empty string for prose-only answers.'
        )
    )


class RenderChartSpec(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(RenderChartSpecSignature)

    def forward(self, rows: str, intent: str) -> dspy.Prediction:
        return self.predict(rows=rows, intent=intent)
