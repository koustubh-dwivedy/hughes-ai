"""Formats and prints eval results — per-question table, category breakdown,
per-tier summary (HUG-188)."""

from __future__ import annotations

from nl_engine.benchmarks.grader import GradeResult, TierSummary

# Categories shown in the failure breakdown, in display order.
_CATEGORY_DISPLAY_ORDER = (
    "wrong_rows",
    "no_rows",
    "sql_error",
    "missing_table",
    "parse_error",
    "wrong_columns",
    "clarification_missed",
    "mf_unsupported",
)


def _fmt_optional(v: float | None) -> str:
    return "-" if v is None else f"{v:.2f}"


def _print_per_question_table(results: list[GradeResult]) -> None:
    cols = (
        f"{'#':>3}  {'Type':<18}  Ok  {'SqlV':>4}"
        f"  {'Tbl':>5}  {'Kw':>5}  Question"
    )
    print(f"\n{cols}")  # noqa: T201
    print("-" * 88)  # noqa: T201
    for i, r in enumerate(results, 1):
        mark = "✓" if r.correct else "✗"
        sql_v = (
            "-"
            if r.sql_valid is None
            else ("✓" if r.sql_valid else "✗")
        )
        tbl = _fmt_optional(r.table_equivalence)
        kw = _fmt_optional(r.keyword_frac)
        question = r.question[:60]
        print(  # noqa: T201
            f"{i:>3}  {r.question_type:<18}  {mark:>2}  {sql_v:>4}  "
            f"{tbl:>5}  {kw:>5}  {question}"
        )


def _print_failures_by_category(results: list[GradeResult]) -> None:
    counts: dict[str, int] = {}
    for r in results:
        if r.correct:
            continue
        counts[r.category] = counts.get(r.category, 0) + 1
    if not counts:
        return
    parts = []
    for cat in _CATEGORY_DISPLAY_ORDER:
        parts.append(f"{cat}={counts.get(cat, 0)}")
    # Surface any categories produced that aren't in the display order.
    for cat in sorted(set(counts) - set(_CATEGORY_DISPLAY_ORDER)):
        parts.append(f"{cat}={counts[cat]}")
    print("\nFailures by category:")  # noqa: T201
    print("  " + "  ".join(parts))  # noqa: T201
    if counts.get("mf_unsupported"):
        print(  # noqa: T201
            "  (mf_unsupported = semantic-layer gap, not a model failure — "
            "see HUG-191)"
        )


def _print_tier_summaries(tier_summaries: list[TierSummary]) -> None:
    print("")  # noqa: T201
    for t in tier_summaries:
        gate_part = (
            f" (gate: {t.threshold:.0f}%)"
            if t.threshold is not None
            else ""
        )
        if t.status == "EMPTY":
            print(  # noqa: T201
                f"{t.name.title():12} 0/0 — EMPTY{gate_part}"
            )
            continue
        print(  # noqa: T201
            f"{t.name.title():12} {t.correct}/{t.total} "
            f"({t.accuracy:.1f}%) — {t.status}{gate_part}"
        )


def _print_overall(results: list[GradeResult]) -> None:
    correct = sum(1 for r in results if r.correct)
    total = len(results)
    accuracy = correct / total * 100 if total else 0.0
    print(  # noqa: T201
        f"\nOverall:     {correct}/{total} ({accuracy:.1f}%)\n"
    )


def print_report(
    results: list[GradeResult],
    tier_summaries: list[TierSummary],
) -> None:
    """Render the full eval report.

    Sections (top to bottom):
      1. Per-question table (one row per question).
      2. Failures by category — only shown if there are failures.
      3. Per-tier summary — must-pass + long-tail with PASS / FAIL / WARN /
         EMPTY status.
      4. Overall summary — total correct / total.
    """
    _print_per_question_table(results)
    _print_failures_by_category(results)
    _print_tier_summaries(tier_summaries)
    _print_overall(results)
