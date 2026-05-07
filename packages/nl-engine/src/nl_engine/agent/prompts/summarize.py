"""DSPy module: produce a terse English summary of an MF result set."""

from __future__ import annotations

import dspy


class SummarizeSignature(dspy.Signature):
    """Write a 1-2 sentence answer that stands on its own.

    Rules:
      * State the metric value first (or the headline insight).
      * Quote the time window and any active filter from the query.
      * Use the metric definition to choose unit + framing — e.g.
        ratios shown as percentages, currency shown with the right
        precision.
      * Avoid hedging ("approximately") unless the rows include nulls
        or notes that justify it.
      * Plain English. No markdown bullet lists or code blocks.
    """

    rows: str = dspy.InputField(
        desc="JSON array of result rows (flat dicts)."
    )
    mf_query: str = dspy.InputField(
        desc="JSON of the MF query that produced these rows."
    )
    metric_definition: str = dspy.InputField(
        desc=(
            "Description of the metric (formula, unit, caveats). "
            "Sourced from docs/metrics.md / the catalog."
        ),
        default="",
    )
    summary: str = dspy.OutputField(
        desc="The 1-2 sentence answer ready to render to the user."
    )


class Summarize(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(SummarizeSignature)

    def forward(
        self, rows: str, mf_query: str, metric_definition: str = ""
    ) -> dspy.Prediction:
        return self.predict(
            rows=rows,
            mf_query=mf_query,
            metric_definition=metric_definition,
        )
