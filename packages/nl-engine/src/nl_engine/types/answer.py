"""Answer / clarification response shapes used by the grader.

Surface 1 used to own these types in `nl_engine.engine`. After Surface 1
was retired (HUG-193) the eval grader still needs a uniform shape to
compare both clarification turns and answered turns against ground
truth. Keeping these types out of `agent` so the grader has no agent
import dependency.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnswerResponse:
    sql: str
    explanation: str
    tables_used: list[str]
    assumptions: list[str]
    caveats: list[str]
    rows: list[dict[str, object]]
    columns: list[str]


@dataclass
class ClarificationResponse:
    question: str
