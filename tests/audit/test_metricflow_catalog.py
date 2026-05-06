"""Audit: every metric named in packages/nl-engine/context/metrics.yaml has a
counterpart in MetricFlow's catalog (HUG-174).

This catches drift when someone adds a new prose metric without translating
it into a MetricFlow definition (or removes one without cleaning up).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROSE_METRICS = (
    _REPO_ROOT / "packages" / "nl-engine" / "context" / "metrics.yaml"
)
_MF_METRICS = (
    _REPO_ROOT / "packages" / "dbt-models" / "models" / "semantic" / "metrics.yml"
)


def _prose_metric_names() -> set[str]:
    raw = yaml.safe_load(_PROSE_METRICS.read_text())
    return {m["name"] for m in raw["metrics"]}


def _mf_metric_names() -> set[str]:
    raw = yaml.safe_load(_MF_METRICS.read_text())
    return {m["name"] for m in raw["metrics"]}


def test_every_prose_metric_has_mf_counterpart() -> None:
    prose = _prose_metric_names()
    mf = _mf_metric_names()
    missing = sorted(prose - mf)
    assert not missing, (
        "prose metrics with no MetricFlow counterpart "
        f"(metrics.yaml needs translation in metrics.yml): {missing}"
    )


def test_no_orphan_mf_metrics() -> None:
    """Every MetricFlow metric should appear in prose grounding (or be a
    helper metric explicitly named to support a ratio numerator / denominator)."""
    prose = _prose_metric_names()
    mf = _mf_metric_names()
    # Helpers we deliberately added in MF that aren't in prose grounding.
    helpers = {
        "delinquent_balance",       # numerator for delinquency_rate ratio
        "requested_amount_total",   # exposed for grounding completeness
        "funded_count",             # ratio numerator + standalone metric
        "funded_amount_total",      # standalone funded-volume metric
        "loan_count",               # standalone metric
        "past_due_loan_count",      # exposed for past-due slicing
        "weighted_avg_loan_rate",   # mart-derived weighted rate
        "lifecycle_event_count",    # named-twin of watchlist_count for
                                    # lifecycle questions (HUG-190 must-pass-023)
    }
    orphans = sorted((mf - prose) - helpers)
    assert not orphans, (
        "MetricFlow metrics not in prose grounding (and not in known "
        f"helper allowlist): {orphans}"
    )


@pytest.mark.parametrize(
    "metric_name",
    sorted(yaml.safe_load(_MF_METRICS.read_text())["metrics"], key=lambda m: m["name"]),
    ids=lambda m: m["name"] if isinstance(m, dict) else str(m),
)
def test_each_mf_metric_has_required_fields(metric_name: dict) -> None:
    """Every metric must declare name + description + label + type + type_params."""
    required = {"name", "description", "label", "type", "type_params"}
    missing = required - set(metric_name.keys())
    assert not missing, (
        f"metric {metric_name.get('name', '?')} missing fields: {missing}"
    )
