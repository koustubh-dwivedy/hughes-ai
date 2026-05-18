"""Tests for HUG-263 — API lifespan pre-warms the `mf query` subprocess
path so the first user request doesn't pay the 51 s manifest-parse cost
that was observed on 2026-05-18.

These tests opt OUT of the conftest's `API_WARM_CATALOG=0` session fixture
because the whole point is to exercise the warmup branch.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def _force_warmup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_WARM_CATALOG", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


def test_lifespan_invokes_mf_query_after_list_metrics(
    _force_warmup_env: None,
) -> None:
    """The lifespan should call mf.query exactly once with the FIRST
    metric returned by mf.list_metrics — this primes the semantic
    manifest parse for the mf_query path."""
    from nl_engine.repo.metricflow import MfMetric

    fake_metrics = [
        MfMetric(name="metric_alpha", dimensions=["d1"]),
        MfMetric(name="metric_beta", dimensions=["d2"]),
    ]

    query_calls: list[dict[str, Any]] = []

    def _fake_query(metric: str, **kwargs: Any) -> Any:
        query_calls.append({"metric": metric, **kwargs})
        return object()

    with (
        patch("nl_engine.repo.metricflow.list_metrics", return_value=fake_metrics),
        patch("nl_engine.repo.metricflow.query", side_effect=_fake_query),
        # HUG-266: lifespan also calls turn_state.cleanup_stale when
        # API_WARM_CATALOG=1 (the same flag that gates the mf warmup).
        patch("api.repo.turn_state.cleanup_stale", return_value=0),
    ):
        from api.main import app

        with TestClient(app):
            pass  # entering + exiting context triggers lifespan

    assert len(query_calls) == 1
    assert query_calls[0]["metric"] == "metric_alpha"
    assert query_calls[0]["limit"] == 1


def test_lifespan_warmup_failure_is_non_fatal(
    _force_warmup_env: None,
) -> None:
    """An mf.query exception during prewarm must NOT prevent API startup —
    the user's first query will pay the cold-start cost but the service
    is still up. We only assert no exception propagates."""
    from nl_engine.repo.metricflow import MetricFlowError, MfMetric

    def _explode(metric: str, **kwargs: Any) -> Any:
        raise MetricFlowError("synthetic prewarm failure")

    fake_metrics = [MfMetric(name="metric_alpha", dimensions=[])]

    with (
        patch("nl_engine.repo.metricflow.list_metrics", return_value=fake_metrics),
        patch("nl_engine.repo.metricflow.query", side_effect=_explode),
        patch("api.repo.turn_state.cleanup_stale", return_value=0),
    ):
        from api.main import app

        with TestClient(app):
            pass


def test_lifespan_skips_warmup_when_no_metrics(_force_warmup_env: None) -> None:
    """When list_metrics returns an empty list (e.g., catalog unbuilt),
    we should not crash trying to dereference metrics[0]."""
    query_calls: list[Any] = []

    def _fake_query(metric: str, **kwargs: Any) -> Any:
        query_calls.append(metric)
        return object()

    with (
        patch("nl_engine.repo.metricflow.list_metrics", return_value=[]),
        patch("nl_engine.repo.metricflow.query", side_effect=_fake_query),
        patch("api.repo.turn_state.cleanup_stale", return_value=0),
    ):
        from api.main import app

        with TestClient(app):
            pass

    assert query_calls == []
