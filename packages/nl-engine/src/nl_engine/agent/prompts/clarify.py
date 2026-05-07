"""DSPy module: produce a clarifying question when the user's intent
is genuinely ambiguous."""

from __future__ import annotations

import dspy


class ClarifySignature(dspy.Signature):
    """Pose ONE concise clarification when the question maps to
    multiple equally-plausible catalog entries or filter ranges.

    Rules:
      * Only emit a question when the ambiguity prevents progress —
        if a reasonable default exists, the agent should answer
        directly instead of asking.
      * Frame the question to elicit a SHORT answer (a single
        choice) rather than free-form prose.
      * If you can offer 2-4 distinct options, populate `options`.
        Otherwise leave it empty and let the user reply naturally.
    """

    question: str = dspy.InputField(desc="The latest user message.")
    ambiguity: str = dspy.InputField(
        desc=(
            "Short description of the ambiguity (e.g. 'two metrics "
            "named ratio_x match', 'no time window specified')."
        )
    )
    clarification: str = dspy.OutputField(
        desc="The clarifying question to render to the user."
    )
    options: str = dspy.OutputField(
        desc="JSON array of suggested answer choices, or '[]'."
    )


class Clarify(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(ClarifySignature)

    def forward(self, question: str, ambiguity: str) -> dspy.Prediction:
        return self.predict(question=question, ambiguity=ambiguity)
