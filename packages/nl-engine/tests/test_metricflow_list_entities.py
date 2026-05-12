"""Unit tests for the `_list_entities_for` helper and its merge into
`list_metrics()`. Driven by a fake `_run` fixture so no real `mf` CLI
invocation is required.
"""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import patch

import pytest
from nl_engine.repo import metricflow as mf


@pytest.fixture(autouse=True)
def _clear_list_metrics_cache() -> Any:
    """list_metrics is lru_cache'd at process scope. Tests that exercise
    it with different fake _run fixtures need a fresh cache each time."""
    mf.list_metrics.cache_clear()
    yield
    mf.list_metrics.cache_clear()


def _fake_run_factory(stdout_by_args: dict[str, str]) -> Any:
    """Build a `_run` replacement keyed by " ".join(args)."""

    def _fake(args: list[str], cwd: Any = None) -> subprocess.CompletedProcess[str]:
        key = " ".join(args)
        if key not in stdout_by_args:
            raise mf.MetricFlowError(f"no fixture for {key!r}")
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=stdout_by_args[key], stderr=""
        )

    return _fake


def test_list_entities_for_parses_bullet_list() -> None:
    fake = _fake_run_factory({
        "list entities --metrics delinquency_rate": (
            "Spinner glyphs ✔ We've found 3 entities for metrics.\n"
            "• branch\n"
            "• officer\n"
            "• product_type\n"
        ),
    })
    with patch.object(mf, "_run", side_effect=fake):
        ents = mf._list_entities_for("delinquency_rate")
    assert ents == ["branch", "officer", "product_type"]


def test_list_metrics_merges_entities_and_dimensions() -> None:
    fake = _fake_run_factory({
        "list metrics": (
            "We've found 1 metrics.\n"
            "• delinquency_rate: branch__branch_name, metric_time and 2 more\n"
        ),
        "list dimensions --metrics delinquency_rate": (
            "We've found 3 dimensions.\n"
            "• branch__branch_name\n"
            "• metric_time\n"
            "• officer__officer_name\n"
        ),
        "list entities --metrics delinquency_rate": (
            "We've found 3 entities.\n"
            "• branch\n"
            "• officer\n"
            "• product_type\n"
        ),
    })
    with patch.object(mf, "_run", side_effect=fake):
        result = mf.list_metrics()
    assert len(result) == 1
    assert result[0].name == "delinquency_rate"
    # Sorted union of dims + entities.
    assert result[0].dimensions == [
        "branch",
        "branch__branch_name",
        "metric_time",
        "officer",
        "officer__officer_name",
        "product_type",
    ]


def test_list_metrics_falls_back_when_entities_call_fails() -> None:
    fake = _fake_run_factory({
        "list metrics": "We've found 1 metrics.\n• total_loan_balance:\n",
        "list dimensions --metrics total_loan_balance": (
            "• as_of_month\n• branch__branch_name\n"
        ),
        # list entities deliberately not in fixtures → MetricFlowError
    })
    with patch.object(mf, "_run", side_effect=fake):
        result = mf.list_metrics()
    assert len(result) == 1
    # Just dims, no entities — no crash.
    assert result[0].dimensions == ["as_of_month", "branch__branch_name"]
