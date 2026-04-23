"""Formats and prints eval results; returns overall accuracy."""

from __future__ import annotations


def print_report(results: list[dict[str, object]], threshold: float) -> float:
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    accuracy = correct / total * 100 if total else 0.0

    cols = (
        f"{'#':>3}  {'Type':<16}  Ok  {'SqlV':>4}"
        f"  {'Tbl':>5}  {'Kw':>5}  Question"
    )
    print(f"\n{cols}")  # noqa: T201
    print("-" * 88)  # noqa: T201
    for i, r in enumerate(results, 1):
        mark = "✓" if r["correct"] else "✗"
        sql_v = "-" if r["sql_valid"] is None else ("✓" if r["sql_valid"] else "✗")
        tbl = "-" if r["table_jaccard"] is None else f"{r['table_jaccard']:.2f}"
        kw = "-" if r["keyword_frac"] is None else f"{r['keyword_frac']:.2f}"
        question = str(r["question"])[:60]
        qtype = str(r["question_type"])
        print(  # noqa: T201
            f"{i:>3}  {qtype:<18}  {mark:>2}  {sql_v:>4}  {tbl:>5}  {kw:>5}  {question}"
        )

    status = "PASS" if accuracy >= threshold else "FAIL"
    summary = (
        f"\nOverall: {correct}/{total} ({accuracy:.1f}%)"
        f" — {status} (threshold: {threshold:.0f}%)\n"
    )
    print(summary)  # noqa: T201
    return accuracy
