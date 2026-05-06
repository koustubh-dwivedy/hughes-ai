"""Pure matching helpers used by the grader."""

from __future__ import annotations

from typing import Any

# Thresholds for the structural fallback path (no ground_truth_rows).
TABLE_EQUIV_THRESHOLD = 0.7
KEYWORD_FRAC_THRESHOLD = 0.6

# MetricFlow appends a time-grain suffix to the synthetic time-dimension
# column it returns (e.g., `kpi_month__as_of_month__month`). The set
# matches MetricFlow's `TimeGranularity` enum.
_MF_TIME_GRAIN_SUFFIXES: tuple[str, ...] = (
    "__second", "__minute", "__hour", "__day", "__week",
    "__month", "__quarter", "__year",
)


def normalize_column_name(col: str) -> str:
    """Collapse a MetricFlow column ID to its semantically meaningful tail.

    MetricFlow returns column names like ``deposits_monthly_grain__branch``
    (semantic-model prefix + dimension), or
    ``kpi_month__as_of_month__month`` (semantic-model prefix + dimension +
    time-grain suffix). The grader's ground truth uses the bare
    user-facing names (``branch``, ``as_of_month``). This collapses the MF
    form to that bare name so the comparison is meaningful:

      - strip a trailing time-grain suffix (`__month`, `__day`, etc.) once
      - take the last `__`-separated segment

    Bare metric names (no `__`) pass through unchanged.
    """
    for suffix in _MF_TIME_GRAIN_SUFFIXES:
        if col.endswith(suffix):
            col = col[: -len(suffix)]
            break
    if "__" in col:
        col = col.rsplit("__", 1)[-1]
    return col


def table_equivalence(
    expected: list[str],
    actual: list[str],
    equivalent_groups: list[list[str]] | None = None,
) -> float:
    """Jaccard with `equivalent_groups` collapsed to canonical tokens.

    Empty `expected` → 1.0 (vacuously satisfied).
    """
    canonical: dict[str, str] = {}
    for group in equivalent_groups or []:
        if not group:
            continue
        rep = group[0]
        for name in group:
            canonical[name] = rep
    e = {canonical.get(n, n) for n in expected}
    a = {canonical.get(n, n) for n in actual}
    if not e:
        return 1.0
    union = e | a
    return len(e & a) / len(union) if union else 1.0


def keyword_frac(expected: list[str], sql: str) -> float:
    """Fraction of `expected` keywords appearing in `sql`. Case-insensitive."""
    if not expected:
        return 1.0
    upper = sql.upper()
    matched = sum(1 for kw in expected if kw.upper() in upper)
    return matched / len(expected)


def _normalize_value(v: Any, tolerance: float) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and tolerance > 0:
        return round(v / tolerance) * tolerance
    return v


def _row_sort_key(row: dict[str, Any], tolerance: float) -> tuple[Any, ...]:
    return tuple(
        sorted((k, str(_normalize_value(v, tolerance))) for k, v in row.items())
    )


_BOOL_STRING_TRUE = {"true", "True", "TRUE"}
_BOOL_STRING_FALSE = {"false", "False", "FALSE"}


def _coerce_for_compare(v: Any) -> Any:
    """MetricFlow returns numeric and boolean column values as quoted
    strings via the JSON tool-call surface (the LLM sees them as strings
    and copies them verbatim into final_answer.rows). Coerce on the way
    in so numeric comparisons + tolerance logic and bool equality
    actually fire."""
    if v is None:
        return v
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s in _BOOL_STRING_TRUE:
            return True
        if s in _BOOL_STRING_FALSE:
            return False
        try:
            return float(s)
        except (TypeError, ValueError):
            return v
    return v


def _values_equal(expected: Any, actual: Any, tolerance: float) -> bool:
    e = _coerce_for_compare(expected)
    a = _coerce_for_compare(actual)
    if isinstance(e, bool) or isinstance(a, bool):
        return bool(e == a)
    if isinstance(e, (int, float)) and isinstance(a, (int, float)):
        if e == 0:
            return abs(a) <= tolerance
        return abs(e - a) / abs(e) <= tolerance
    return bool(e == a)


def _diff_first_mismatch(
    e_row: dict[str, Any],
    a_row: dict[str, Any],
    index: int,
    tolerance: float,
) -> str | None:
    e_keys = set(e_row.keys())
    a_keys = set(a_row.keys())
    if e_keys != a_keys:
        return (
            f"row {index}: column keys differ — "
            f"expected={sorted(e_keys)}, actual={sorted(a_keys)}"
        )
    for k in e_keys:
        if not _values_equal(e_row[k], a_row[k], tolerance):
            return (
                f"row {index}, column {k!r}: "
                f"expected={e_row[k]!r}, actual={a_row[k]!r}"
            )
    return None


def _normalize_row(
    row: dict[str, Any], expected_keys: set[str]
) -> dict[str, Any]:
    """Project a row's keys through `normalize_column_name` and keep only
    those that appear in `expected_keys`. Ignores extras the agent picked
    up alongside the answer (e.g., the time-dim that MetricFlow
    auto-attaches when grouping by `metric_time__month`)."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        norm = normalize_column_name(k)
        if norm in expected_keys:
            out[norm] = v
    return out


def rowset_match(
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    tolerance: float = 0.01,
) -> tuple[bool, str]:
    """Order-insensitive row comparison; numeric values within `tolerance`.

    Column-name normalization (see `normalize_column_name`) is applied
    before comparison. Extra columns in `actual` beyond what `expected`
    declares are ignored — they often arise because MetricFlow attaches
    a time-dim alongside the metric, which the answer is still correct
    despite.

    Returns (matched, diff_message). diff_message is empty on match.
    """
    if len(expected) != len(actual):
        return False, (
            f"row count mismatch: expected={len(expected)}, actual={len(actual)}"
        )
    if not expected:
        return True, ""
    expected_keys = {normalize_column_name(k) for k in expected[0]}
    e_norm = [_normalize_row(r, expected_keys) for r in expected]
    a_norm = [_normalize_row(r, expected_keys) for r in actual]
    e_sorted = sorted(e_norm, key=lambda r: _row_sort_key(r, tolerance))
    a_sorted = sorted(a_norm, key=lambda r: _row_sort_key(r, tolerance))
    for i, (e_row, a_row) in enumerate(zip(e_sorted, a_sorted, strict=False)):
        diff = _diff_first_mismatch(e_row, a_row, i, tolerance)
        if diff:
            return False, diff
    return True, ""


def columnset_match(
    expected: list[str],
    actual: list[str],
) -> tuple[bool, str]:
    """Subset semantics on normalized column names: every expected column
    must appear in actual after `normalize_column_name`. Extra actual
    columns are allowed — see `rowset_match` rationale."""
    e = {normalize_column_name(c) for c in expected}
    a = {normalize_column_name(c) for c in actual}
    missing = e - a
    if not missing:
        return True, ""
    return False, f"missing: {sorted(missing)}"
