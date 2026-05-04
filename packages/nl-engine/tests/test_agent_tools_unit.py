"""Unit tests for the agent tools that don't require a live MetricFlow.

`mf_query` retry behavior is exercised here against a fake metricflow
module installed via monkeypatch — keeps the test deterministic and
fast (no `mf` subprocess invocation)."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from nl_engine.agent.tools import (
    clarify,
    final_answer,
    mf_query,
)


def _install_fake_metricflow(
    monkeypatch: pytest.MonkeyPatch, behavior: list[Any]
) -> None:
    """Replace `nl_engine.repo.metricflow` with a fake walking `behavior`.
    Each entry is either an Exception (raised) or a result dict (returned)."""
    fake_mf = types.ModuleType("nl_engine.repo.metricflow")
    state = {"i": 0}

    class _Result:
        def __init__(
            self,
            metric: str,
            dimensions: list[str],
            rows: list[dict[str, Any]],
        ):
            self.metric = metric
            self.dimensions = dimensions
            self.rows = rows

    def _query(metric: str, **kwargs: Any) -> Any:
        idx = state["i"]
        state["i"] += 1
        outcome = behavior[idx]
        if isinstance(outcome, Exception):
            raise outcome
        return _Result(metric, kwargs.get("dimensions") or [], outcome["rows"])

    fake_mf.query = _query  # type: ignore[attr-defined]
    fake_mf.list_metrics = lambda: []  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "nl_engine.repo.metricflow", fake_mf)


def test_mf_query_succeeds_on_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_metricflow(monkeypatch, [{"rows": [{"x": 1}]}])
    out = mf_query.invoke({"metric": "total_loans"})
    assert out["metric"] == "total_loans"
    assert out["rows"] == [{"x": 1}]


def test_mf_query_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_metricflow(
        monkeypatch,
        [RuntimeError("transient"), RuntimeError("transient"), {"rows": [{"x": 2}]}],
    )
    out = mf_query.invoke({"metric": "total_loans"})
    assert out["rows"] == [{"x": 2}]


def test_mf_query_gives_up_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_metricflow(
        monkeypatch,
        [RuntimeError("a"), RuntimeError("b"), RuntimeError("c")],
    )
    with pytest.raises(RuntimeError, match="mf_query failed after retries"):
        mf_query.invoke({"metric": "total_loans"})


def test_clarify_returns_typed_payload() -> None:
    out = clarify.invoke({"question": "Which?", "options": ["a", "b"]})
    assert out == {"question": "Which?", "options": ["a", "b"]}


def test_final_answer_returns_typed_payload() -> None:
    out = final_answer.invoke({"summary": "done", "rows": [{"x": 1}]})
    assert out["summary"] == "done"
    assert out["rows"] == [{"x": 1}]
    assert out["openui_dsl"] is None
