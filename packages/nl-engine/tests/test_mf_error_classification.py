"""Unit tests for the mf_query error classifier (HUG-190 Phase B).

Verifies that structural errors return immediately as `{"error",
"hint"}` payloads (so the agent can correct on the next call) and
that transient errors get one retry before giving up.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from nl_engine.agent import tools


def test_classify_structural_no_join_path() -> None:
    exc = RuntimeError(
        "No valid join paths exist from the measure to the group-by-item"
    )
    assert tools.classify_mf_error(exc) == "structural"


def test_classify_structural_order_mismatch() -> None:
    exc = RuntimeError(
        "The order-by item 'desc' does not match exactly one of the query items"
    )
    assert tools.classify_mf_error(exc) == "structural"


def test_classify_structural_unknown_column() -> None:
    exc = RuntimeError("ERROR: Database Error column \"event_month\" does not exist")
    assert tools.classify_mf_error(exc) == "structural"


def test_classify_structural_validation_error() -> None:
    exc = RuntimeError("Got error(s) during query resolution.")
    assert tools.classify_mf_error(exc) == "structural"


def test_classify_transient_timeout() -> None:
    exc = RuntimeError("subprocess timed out after 30s")
    assert tools.classify_mf_error(exc) == "transient"


def test_classify_transient_connection() -> None:
    exc = RuntimeError("connection refused on port 5432")
    assert tools.classify_mf_error(exc) == "transient"


def test_classify_transient_oom() -> None:
    exc = RuntimeError("mf process exit -9 (oom-killed)")
    assert tools.classify_mf_error(exc) == "transient"


def test_classify_unknown_defaults_to_structural() -> None:
    """Conservative default: unknown error patterns get surfaced
    immediately rather than retried, so the agent sees them sooner."""
    exc = RuntimeError("something completely novel happened")
    assert tools.classify_mf_error(exc) == "structural"


def test_extract_mf_hint_pulls_did_you_mean_list() -> None:
    msg = (
        "No valid join paths exist from the measure to the group-by-item"
        " 'branch_name', with suggestions: ['branch',"
        " 'deposits_monthly_grain__branch']"
    )
    hint = tools.extract_mf_hint(msg)
    assert hint is not None
    assert "deposits_monthly_grain__branch" in hint


def test_extract_mf_hint_returns_none_when_no_suggestion() -> None:
    msg = "ERROR: Database Error column does not exist"
    assert tools.extract_mf_hint(msg) is None


def _patch_mf_query_once(side_effect: list[Any]) -> Any:
    """Build a side_effect for _mf_query_once that yields each value in turn."""
    iterator = iter(side_effect)

    def fake(_args: tools.MfQueryArgs) -> dict[str, Any]:
        outcome = next(iterator)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return fake


def test_mf_query_structural_error_returns_payload_no_retry() -> None:
    err = RuntimeError(
        "The order-by item 'desc' does not match exactly one of the query items"
    )
    fake = _patch_mf_query_once([err])
    with patch("nl_engine.agent.tools._mf_query_once", side_effect=fake):
        result = tools.mf_query.invoke({"metric": "loan_to_deposit_ratio"})
    assert isinstance(result, dict)
    assert "error" in result
    assert "does not match" in result["error"]


def test_mf_query_transient_retries_once_then_succeeds() -> None:
    success_payload = {"metric": "x", "dimensions": [], "rows": [{"x": 1}]}
    fake = _patch_mf_query_once([RuntimeError("connection refused"), success_payload])
    with (
        patch("nl_engine.agent.tools._mf_query_once", side_effect=fake),
        patch("nl_engine.agent.tools.time.sleep"),
    ):
        result = tools.mf_query.invoke({"metric": "x"})
    assert result == success_payload


def test_mf_query_transient_then_structural_returns_payload() -> None:
    fake = _patch_mf_query_once(
        [
            RuntimeError("timeout"),
            RuntimeError("did you mean: ['actual_column']"),
        ]
    )
    with (
        patch("nl_engine.agent.tools._mf_query_once", side_effect=fake),
        patch("nl_engine.agent.tools.time.sleep"),
    ):
        result = tools.mf_query.invoke({"metric": "x"})
    assert isinstance(result, dict)
    assert "error" in result
    assert "hint" in result
    assert "actual_column" in result["hint"]


def test_mf_query_transient_retried_once_then_propagates_error() -> None:
    fake = _patch_mf_query_once(
        [RuntimeError("connection refused"), RuntimeError("connection refused again")]
    )
    with (
        patch("nl_engine.agent.tools._mf_query_once", side_effect=fake),
        patch("nl_engine.agent.tools.time.sleep"),
    ):
        result = tools.mf_query.invoke({"metric": "x"})
    assert isinstance(result, dict)
    assert "error" in result
    assert "again" in result["error"]


@pytest.mark.parametrize(
    "marker",
    [
        "does not match exactly one of the query items",
        "no valid join paths exist",
        "did you mean",
        "column does not exist",
    ],
)
def test_all_structural_markers_classify_correctly(marker: str) -> None:
    assert tools.classify_mf_error(RuntimeError(marker)) == "structural"
