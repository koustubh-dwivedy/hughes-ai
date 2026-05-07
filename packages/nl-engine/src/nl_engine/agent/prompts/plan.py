"""DSPy module: pick the next agent action for an incoming user turn.

Outputs one of the abstract actions the ReAct agent can take:
  - `query_data`     : reach for `mf_query` next.
  - `lookup_metric`  : reach for `list_metrics` / `lookup_metric_definition`.
  - `clarify`        : ask the user a clarification question.
  - `final_answer`   : answer directly from prior turn context.

This is the "plan" step the ReAct loop expresses implicitly via tool
choice. Surfacing it as a typed DSPy module lets the optimizer tune
which signal (question shape, history length, missing dimensions)
should trigger which action.
"""

from __future__ import annotations

from typing import Literal

import dspy

ActionT = Literal["query_data", "lookup_metric", "clarify", "final_answer"]


class PlanQuestionSignature(dspy.Signature):
    """Decide the next high-level action for the agent.

    Read the user's question + the prior conversation + the available
    metric catalog. Pick the SINGLE action most likely to make progress.
    Prefer `query_data` whenever the question references a metric you
    can resolve to a catalog entry. Use `clarify` only when multiple
    catalog metrics could equally answer the question.
    """

    question: str = dspy.InputField(desc="The latest user message.")
    conversation_history: str = dspy.InputField(
        desc="Recent prior turns as 'role: content' lines, oldest first.",
        default="",
    )
    available_metrics: str = dspy.InputField(
        desc="Comma-separated list of metric names from the catalog.",
    )
    rationale: str = dspy.OutputField(
        desc="One sentence on why this action was chosen.",
    )
    action: ActionT = dspy.OutputField(
        desc="One of: query_data, lookup_metric, clarify, final_answer.",
    )


class PlanQuestion(dspy.Module):
    """Hand-written predictor used as the starting point for compilation."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(PlanQuestionSignature)

    def forward(
        self,
        question: str,
        available_metrics: str,
        conversation_history: str = "",
    ) -> dspy.Prediction:
        return self.predict(
            question=question,
            available_metrics=available_metrics,
            conversation_history=conversation_history,
        )
