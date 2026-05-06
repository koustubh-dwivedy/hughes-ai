"""Render the eval report — single-column agent path, per-tier summaries,
and category breakdown. Surface 1 was retired in HUG-193, so the legacy
column is gone; only the agent path is reported now.
"""

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


def _summarize_failures(results: list[GradeResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in results:
        if r.correct:
            continue
        counts[r.category] = counts.get(r.category, 0) + 1
    return counts


def _format_failure_line(counts: dict[str, int]) -> str:
    parts = [f"{cat}={counts.get(cat, 0)}" for cat in _CATEGORY_DISPLAY_ORDER]
    for cat in sorted(set(counts) - set(_CATEGORY_DISPLAY_ORDER)):
        parts.append(f"{cat}={counts[cat]}")
    return "  ".join(parts)


def _print_agent_per_question_table(results: list[GradeResult]) -> None:
    cols = (
        f"{'#':>3}  {'Type':<18}  Ok  {'Category':<22}  Question"
    )
    print(f"\n=== Agent path (LangGraph + MetricFlow) ===\n{cols}")  # noqa: T201
    print("-" * 88)  # noqa: T201
    if not results:
        print("(no questions met the agent-grading criteria — see HUG-189)")  # noqa: T201
        return
    for i, r in enumerate(results, 1):
        mark = "✓" if r.correct else "✗"
        print(  # noqa: T201
            f"{i:>3}  {r.question_type:<18}  {mark:>2}  {r.category:<22}  "
            f"{r.question[:60]}"
        )


def _print_failures_section(
    title: str, results: list[GradeResult]
) -> None:
    counts = _summarize_failures(results)
    if not counts:
        return
    print(f"\n{title}:")  # noqa: T201
    print("  " + _format_failure_line(counts))  # noqa: T201
    if counts.get("mf_unsupported"):
        print(  # noqa: T201
            "  (mf_unsupported = semantic-layer gap, not a model failure — "
            "see HUG-191)"
        )


def _print_tier_block(label: str, tiers: list[TierSummary]) -> None:
    print(f"\n{label}:")  # noqa: T201
    for t in tiers:
        gate_part = (
            f" (gate: {t.threshold:.0f}%)" if t.threshold is not None else ""
        )
        if t.status == "EMPTY":
            print(f"  {t.name.title():12} 0/0 — EMPTY{gate_part}")  # noqa: T201
            continue
        print(  # noqa: T201
            f"  {t.name.title():12} {t.correct}/{t.total} "
            f"({t.accuracy:.1f}%) — {t.status}{gate_part}"
        )


def _print_avg_calls(avg_calls: float, budget: float) -> None:
    flag = "⚠ " if avg_calls > budget else ""
    print(  # noqa: T201
        f"\nagent_avg_calls_per_turn = {flag}{avg_calls:.2f} (budget: {budget:.1f})"
    )


def _print_overall_line(agent: list[GradeResult]) -> None:
    n = len(agent)
    ok = sum(1 for r in agent if r.correct)
    pct = ok / n * 100 if n else 0.0
    print("")  # noqa: T201
    if n:
        print(f"Agent overall: {ok}/{n} ({pct:.1f}%)")  # noqa: T201
    else:
        print("Agent overall: (no gradable questions on this run)")  # noqa: T201


def print_agent_report(
    agent_results: list[GradeResult],
    agent_tiers: list[TierSummary],
    avg_calls_per_turn: float,
    avg_calls_budget: float,
) -> None:
    """Render the agent-path eval report (single-path after HUG-193).

    Sections (top to bottom):
      1. Per-question table.
      2. Failures by category — only shown if there are failures.
      3. Per-tier summary — status can be PASS/FAIL/WARN/EMPTY.
      4. agent_avg_calls_per_turn — flagged with ⚠ if over budget.
      5. Overall summary line.
    """
    _print_agent_per_question_table(agent_results)
    _print_failures_section("Agent failures by category", agent_results)
    _print_tier_block("Agent tier summary", agent_tiers)
    _print_avg_calls(avg_calls_per_turn, avg_calls_budget)
    _print_overall_line(agent_results)
