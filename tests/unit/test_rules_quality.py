"""Quality gate: new rules must have non-empty id, rule statement, and rationale."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "packages" / "nl-engine" / "src"))

from nl_engine.context_loader import load_all

_NEW_RULE_IDS = {
    "deposit_balance_as_of",
    "deposit_product_taxonomy",
    "officer_attribution",
    "watchlist_definition",
    "nonperforming_definition",
    "mtd_definition",
    "ytd_definition",
    "top_n_default_25",
    "aging_buckets",
}


@pytest.fixture(scope="module")
def rules() -> dict:
    return {r.id: r for r in load_all().rules}


def test_all_new_rules_present(rules: dict) -> None:
    missing = _NEW_RULE_IDS - rules.keys()
    assert not missing, f"Missing rules: {missing}"


def test_new_rules_have_rule_statement(rules: dict) -> None:
    for rule_id in _NEW_RULE_IDS:
        assert rules[rule_id].rule.strip(), f"{rule_id}: rule statement is empty"


def test_new_rules_have_rationale(rules: dict) -> None:
    for rule_id in _NEW_RULE_IDS:
        assert rules[rule_id].rationale.strip(), f"{rule_id}: rationale is empty"
