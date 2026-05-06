"""Unit tests for grader matching helpers (HUG-188)."""

from __future__ import annotations

import pytest
from nl_engine.benchmarks.grader import (
    columnset_match,
    keyword_frac,
    rowset_match,
    table_equivalence,
)

# ── table_equivalence ────────────────────────────────────────────────────────


def test_table_equivalence_empty_expected_returns_one() -> None:
    assert table_equivalence([], ["fct_x"]) == 1.0


def test_table_equivalence_perfect_overlap() -> None:
    assert table_equivalence(["a", "b"], ["a", "b"]) == 1.0


def test_table_equivalence_partial_overlap() -> None:
    assert table_equivalence(["a", "b"], ["a", "c"]) == pytest.approx(1 / 3)


def test_table_equivalence_collapses_via_groups() -> None:
    eq = table_equivalence(
        expected=["fct_deposits_monthly"],
        actual=["deposit_accounts"],
        equivalent_groups=[["fct_deposits_monthly", "deposit_accounts"]],
    )
    assert eq == 1.0


def test_table_equivalence_no_overlap_no_groups() -> None:
    assert table_equivalence(["a"], ["b"]) == 0.0


def test_table_equivalence_empty_group_ignored() -> None:
    assert table_equivalence(["a"], ["a"], equivalent_groups=[[]]) == 1.0


# ── keyword_frac ─────────────────────────────────────────────────────────────


def test_keyword_frac_empty_expected_returns_one() -> None:
    assert keyword_frac([], "SELECT 1") == 1.0


def test_keyword_frac_all_present() -> None:
    assert keyword_frac(["count", "from"], "SELECT COUNT(*) FROM t") == 1.0


def test_keyword_frac_partial() -> None:
    assert keyword_frac(["count", "missing"], "SELECT COUNT(*) FROM t") == 0.5


def test_keyword_frac_case_insensitive() -> None:
    assert keyword_frac(["SELECT", "from"], "select 1 FROM t") == 1.0


# ── rowset_match ─────────────────────────────────────────────────────────────


def test_rowset_match_identical() -> None:
    ok, msg = rowset_match([{"a": 1}], [{"a": 1}])
    assert ok and msg == ""


def test_rowset_match_unordered() -> None:
    ok, _ = rowset_match([{"a": 1}, {"a": 2}], [{"a": 2}, {"a": 1}])
    assert ok


def test_rowset_match_count_mismatch() -> None:
    ok, msg = rowset_match([{"a": 1}], [{"a": 1}, {"a": 2}])
    assert not ok and "row count mismatch" in msg


def test_rowset_match_value_diff_within_tolerance() -> None:
    ok, _ = rowset_match([{"x": 1.0}], [{"x": 1.005}], tolerance=0.01)
    assert ok


def test_rowset_match_value_diff_outside_tolerance() -> None:
    ok, msg = rowset_match([{"x": 1.0}], [{"x": 1.5}], tolerance=0.01)
    assert not ok and "x" in msg


def test_rowset_match_zero_expected_handles_actual_within_tolerance() -> None:
    ok, _ = rowset_match([{"x": 0}], [{"x": 0.005}], tolerance=0.01)
    assert ok


def test_rowset_match_column_keys_differ() -> None:
    """If actual has none of the expected columns (after normalization),
    every expected key is missing in the projected row — surfaced via the
    diff message."""
    ok, msg = rowset_match([{"a": 1}], [{"b": 1}])
    assert not ok and "a" in msg


def test_rowset_match_extra_actual_columns_are_ignored() -> None:
    """HUG-190 (2026-05-07): MetricFlow attaches a time-dim column the
    grader's ground-truth row doesn't declare. Subset semantics — match
    on the projection of expected keys."""
    ok, _ = rowset_match(
        [{"loan_to_deposit_ratio": 0.13}],
        [{"kpi_month__as_of_month__month": "2026-04-01",
          "loan_to_deposit_ratio": 0.13}],
    )
    assert ok


def test_rowset_match_normalizes_metricflow_dimension_keys() -> None:
    """Agent's `deposits_monthly_grain__branch` collapses to GT's `branch`."""
    ok, _ = rowset_match(
        [{"branch": "downtown", "total_balance": 100.0}],
        [{"deposits_monthly_grain__branch": "downtown",
          "deposits_by_branch": 100.0,  # extra metric col — ignored
          "total_balance": 100.0}],
    )
    assert ok


def test_rowset_match_empty_both_passes() -> None:
    ok, msg = rowset_match([], [])
    assert ok and msg == ""


def test_rowset_match_string_values_unchanged() -> None:
    ok, _ = rowset_match([{"label": "auto"}], [{"label": "auto"}])
    assert ok


def test_rowset_match_string_value_diff() -> None:
    ok, msg = rowset_match([{"label": "auto"}], [{"label": "personal"}])
    assert not ok and "label" in msg


# ── columnset_match ──────────────────────────────────────────────────────────


def test_columnset_match_equal() -> None:
    ok, msg = columnset_match(["a", "b"], ["b", "a"])
    assert ok and msg == ""


def test_columnset_match_missing() -> None:
    ok, msg = columnset_match(["a", "b"], ["a"])
    assert not ok and "missing" in msg


def test_columnset_match_allows_extra_actual_columns() -> None:
    """HUG-190 (2026-05-07): subset semantics — extra agent columns are
    fine as long as every expected column is present. MetricFlow attaches
    a time-dim column alongside the metric; that's not a failure."""
    ok, msg = columnset_match(["a"], ["a", "b"])
    assert ok and msg == ""


def test_columnset_match_normalizes_metricflow_dimension_names() -> None:
    """`deposits_monthly_grain__branch` collapses to `branch`; the GT's
    `branch` should match."""
    ok, _ = columnset_match(
        ["branch"], ["deposits_monthly_grain__branch", "deposits_by_branch"]
    )
    assert ok


def test_columnset_match_normalizes_time_grain_suffix() -> None:
    """`kpi_month__as_of_month__month` collapses to `as_of_month`."""
    ok, _ = columnset_match(
        ["as_of_month", "loan_to_deposit_ratio"],
        ["kpi_month__as_of_month__month", "loan_to_deposit_ratio"],
    )
    assert ok
