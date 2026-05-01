"""Integration: new example SQL executes against the seeded DB and returns rows."""
import os
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "packages" / "nl-engine" / "src"))

from nl_engine.context_loader import load_all

_NEW_QUESTIONS = {
    "What is our total deposit balance this month?",
    "What is the deposit breakdown by product type?",
    "Which branch holds the most deposits?",
    "Who are our top 25 depositors?",
    "What is our current blended past due ratio?",
    "Which officers have the most past-due exposure?",
    "Show the delinquency trend by aging bucket over the last 13 months",
    "How many loans are currently on the watchlist?",
    "What is the loan mix by product type this month?",
    "Who are our top 25 borrowers by outstanding balance?",
    "How many single-loan customers do we have by product type?",
    "Show new and paid-off loan events for the most recent month",
    "Show loan-to-deposit ratio trend over the last 13 months",
    "What is our core deposit ratio trend over the past year?",
    "Show monthly loan and deposit growth for the last 12 months",
}


@pytest.fixture(scope="module")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


def test_new_examples_execute(db_url: str) -> None:
    examples = [e for e in load_all().examples if e.question in _NEW_QUESTIONS]
    errors = []
    with psycopg.connect(db_url) as conn:
        for ex in examples:
            try:
                cur = conn.execute(ex.sql)
                rows = cur.fetchall()
                if not rows:
                    errors.append(f"Q: {ex.question!r} returned 0 rows")
            except Exception as exc:
                errors.append(f"Q: {ex.question!r}: {exc}")
    assert not errors, "Example execution failures:\n" + "\n".join(errors)
