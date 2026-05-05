"""Pure matching helpers used by the grader."""

from __future__ import annotations

from typing import Any

# Thresholds for the structural fallback path (no ground_truth_rows).
TABLE_EQUIV_THRESHOLD = 0.7
KEYWORD_FRAC_THRESHOLD = 0.6


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


def _values_equal(expected: Any, actual: Any, tolerance: float) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return bool(expected == actual)
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if expected == 0:
            return abs(actual) <= tolerance
        return abs(expected - actual) / abs(expected) <= tolerance
    return bool(expected == actual)


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


def rowset_match(
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    tolerance: float = 0.01,
) -> tuple[bool, str]:
    """Order-insensitive row comparison; numeric values within `tolerance`.

    Returns (matched, diff_message). diff_message is empty on match.
    """
    if len(expected) != len(actual):
        return False, (
            f"row count mismatch: expected={len(expected)}, actual={len(actual)}"
        )
    if not expected:
        return True, ""
    e_sorted = sorted(expected, key=lambda r: _row_sort_key(r, tolerance))
    a_sorted = sorted(actual, key=lambda r: _row_sort_key(r, tolerance))
    for i, (e_row, a_row) in enumerate(zip(e_sorted, a_sorted, strict=False)):
        diff = _diff_first_mismatch(e_row, a_row, i, tolerance)
        if diff:
            return False, diff
    return True, ""


def columnset_match(
    expected: list[str],
    actual: list[str],
) -> tuple[bool, str]:
    """Order-insensitive column-name set comparison."""
    e = set(expected)
    a = set(actual)
    if e == a:
        return True, ""
    parts = []
    if e - a:
        parts.append(f"missing: {sorted(e - a)}")
    if a - e:
        parts.append(f"extra: {sorted(a - e)}")
    return False, "; ".join(parts)
