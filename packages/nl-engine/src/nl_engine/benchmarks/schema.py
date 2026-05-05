"""Typed schema for benchmark questions YAML.

Loaded by run_eval.py and by HUG-187 / HUG-188 / HUG-189 / HUG-191. All new
fields are optional with defaults so the existing legacy questions parse
without modification — backward-compatible while giving downstream tickets
a single typed shape to author and grade against.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

QuestionType = Literal[
    "origination_volume",
    "approval_rate",
    "funding_rate",
    "delinquency_rate",
    "portfolio_balance",
    "product_mix",
    "channel_mix",
    "edge_case",
    "ambiguous",
    "deposit_balance",
    "deposit_portfolio",
    "past_due",
    "watchlist",
    "loan_portfolio",
    "lifecycle_events",
    "executive_kpi",
]

Category = Literal[
    "dashboard", "metric", "portfolio", "drilldown", "clarification", "edge",
]

Source = Literal[
    "hug-84", "curated-must-pass", "seed", "legacy-import", "synthetic",
]


class Question(BaseModel):
    question: str
    question_type: QuestionType
    expected_tables: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    ground_truth_sql: str | None = None

    id: str | None = None
    category: Category | None = None
    source: Source | None = None
    must_pass: bool = False
    equivalent_tables: list[list[str]] = Field(default_factory=list)
    expected_row_count_estimate: int | None = None
    ground_truth_rows: list[dict[str, object]] | None = None
    expected_metric: str | None = None
    expected_dimensions: list[str] = Field(default_factory=list)


class QuestionsFile(BaseModel):
    questions: list[Question]


def load_questions(path: Path) -> QuestionsFile:
    raw = yaml.safe_load(path.read_text())
    return QuestionsFile.model_validate(raw)
