"""Quality gate: new metrics must have formula, caveats, and ≥3 related_questions."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "packages" / "nl-engine" / "src"))

from nl_engine.context_loader import load_all

_NEW_METRIC_NAMES = {
    # HUG-72: deposit + balance + count
    "total_deposits",
    "mtd_deposit_change",
    "ytd_deposit_change",
    "avg_balance_per_customer",
    "top_n_deposits",
    "deposits_by_product",
    "deposits_by_branch",
    "total_loans",
    "top_n_borrowers",
    "single_loan_customers",
    # HUG-73: ratio + growth + risk
    "past_due_ratio",
    "nonaccrual_balance",
    "watchlist_count",
    "nonperforming_loan_balance",
    "loan_to_deposit_ratio",
    "core_deposit_ratio",
    "monthly_growth_loans",
    "monthly_growth_deposits",
    "rate_spread",
    "delinquency_aging_distribution",
}


@pytest.fixture(scope="module")
def metrics() -> dict:
    return {m.name: m for m in load_all().metrics}


def test_all_new_metrics_present(metrics: dict) -> None:
    missing = _NEW_METRIC_NAMES - metrics.keys()
    assert not missing, f"Missing metrics: {missing}"


def test_new_metrics_have_formula(metrics: dict) -> None:
    for name in _NEW_METRIC_NAMES:
        assert metrics[name].formula_plain_english.strip(), (
            f"{name}: formula_plain_english is empty"
        )


def test_new_metrics_have_caveats(metrics: dict) -> None:
    for name in _NEW_METRIC_NAMES:
        assert metrics[name].caveats.strip(), f"{name}: caveats is empty"


def test_new_metrics_have_three_related_questions(metrics: dict) -> None:
    for name in _NEW_METRIC_NAMES:
        count = len(metrics[name].related_questions)
        assert count >= 3, (
            f"{name}: only {count} related_questions (need ≥3)"
        )
