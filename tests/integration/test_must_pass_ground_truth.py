"""Validation gate for must-pass questions (HUG-187).

For each `must_pass=True` question:
  1. Metadata is complete (id / source / expected_metric for non-ambiguous).
  2. `ground_truth_sql` executes against the seeded DB without error.
  3. `ground_truth_rows` matches the SQL result via rowset_match (HUG-188).

Ambiguous questions (`question_type: ambiguous`) are exempt from #2 and #3 —
they test the agent's clarification path, not row-set accuracy.
"""

from __future__ import annotations

import datetime as _dt
import os
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from nl_engine.benchmarks.grader import rowset_match
from nl_engine.benchmarks.schema import Question, load_questions

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

QUESTIONS_FILE = (
    Path(__file__).parents[2]
    / "packages" / "nl-engine" / "benchmarks" / "questions.yaml"
)


@pytest.fixture(scope="module")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


def _must_pass_questions() -> list[Question]:
    return [q for q in load_questions(QUESTIONS_FILE).questions if q.must_pass]


def _normalize(v: Any) -> Any:
    """Mirror nl_engine.executor._normalize so rowset_match sees JSON-safe shapes."""
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, _dt.datetime):
        return v.isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, _dt.timedelta):
        return str(v)
    return v


def test_must_pass_metadata_complete() -> None:
    """No DB needed — pure metadata check on the YAML."""
    errors: list[str] = []
    for q in _must_pass_questions():
        if not q.id:
            errors.append(f"missing id: {q.question[:60]!r}")
            continue
        if q.source != "curated-must-pass":
            errors.append(
                f"{q.id}: source must be 'curated-must-pass', got {q.source!r}"
            )
        if q.question_type != "ambiguous":
            if not q.expected_metric:
                errors.append(f"{q.id}: expected_metric required for non-ambiguous")
            if not q.ground_truth_sql or not q.ground_truth_sql.strip():
                errors.append(f"{q.id}: ground_truth_sql required")
            if q.ground_truth_rows is None:
                errors.append(f"{q.id}: ground_truth_rows required (strict mode)")
    assert not errors, "must-pass metadata errors:\n  " + "\n  ".join(errors)


def test_must_pass_sql_executes(db_url: str) -> None:
    """Every non-ambiguous must-pass question's SQL must parse + execute."""
    errors: list[str] = []
    with psycopg.connect(db_url) as conn:
        for q in _must_pass_questions():
            if q.question_type == "ambiguous":
                continue
            if not q.ground_truth_sql:
                continue  # already caught by metadata test
            try:
                conn.execute(q.ground_truth_sql).fetchall()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{q.id}: SQL failed: {exc}")
    assert not errors, "must-pass SQL execution errors:\n  " + "\n  ".join(errors)


def test_must_pass_rowset_match(db_url: str) -> None:
    """ground_truth_rows must match the SQL result (1% tolerance on floats)."""
    errors: list[str] = []
    with psycopg.connect(db_url) as conn:
        for q in _must_pass_questions():
            if q.question_type == "ambiguous":
                continue
            if not q.ground_truth_sql or q.ground_truth_rows is None:
                continue  # caught by metadata test
            cur = conn.execute(q.ground_truth_sql)
            cols = [d.name for d in cur.description or []]
            actual = [
                {c: _normalize(v) for c, v in zip(cols, row, strict=False)}
                for row in cur.fetchall()
            ]
            ok, diff = rowset_match(q.ground_truth_rows, actual)
            if not ok:
                errors.append(f"{q.id}: {diff}")
    assert not errors, "must-pass rowset diffs:\n  " + "\n  ".join(errors)
