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


def test_mf_query_transient_retries_once_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient errors (timeout, connection, OOM) get one retry. Anything
    else is classified structural and surfaced immediately. HUG-190."""
    _install_fake_metricflow(
        monkeypatch,
        [RuntimeError("timeout reading subprocess"), {"rows": [{"x": 2}]}],
    )
    monkeypatch.setattr("nl_engine.agent.tools.time.sleep", lambda _s: None)
    out = mf_query.invoke({"metric": "total_loans"})
    assert out["rows"] == [{"x": 2}]


def test_mf_query_structural_error_returns_payload_no_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structural errors (column not found, validation) return an error
    dict on first failure; the agent gets to correct on the next call.
    HUG-190."""
    _install_fake_metricflow(
        monkeypatch,
        [RuntimeError("column 'foo' does not exist; did you mean: ['bar']")],
    )
    out = mf_query.invoke({"metric": "total_loans"})
    assert isinstance(out, dict)
    assert "error" in out
    assert "hint" in out  # 'did you mean' parsed out as hint
    assert "bar" in out["hint"]


def test_mf_query_transient_then_failure_returns_error_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient → retry → transient again → return error payload."""
    _install_fake_metricflow(
        monkeypatch,
        [RuntimeError("connection refused"), RuntimeError("connection refused 2")],
    )
    monkeypatch.setattr("nl_engine.agent.tools.time.sleep", lambda _s: None)
    out = mf_query.invoke({"metric": "total_loans"})
    assert isinstance(out, dict)
    assert "error" in out
    assert "connection refused 2" in out["error"]


def test_clarify_returns_typed_payload() -> None:
    out = clarify.invoke({"question": "Which?", "options": ["a", "b"]})
    assert out == {"question": "Which?", "options": ["a", "b"]}


def test_final_answer_returns_typed_payload() -> None:
    out = final_answer.invoke({"summary": "done", "rows": [{"x": 1}]})
    assert out["summary"] == "done"
    assert out["rows"] == [{"x": 1}]
    assert out["openui_dsl"] is None
