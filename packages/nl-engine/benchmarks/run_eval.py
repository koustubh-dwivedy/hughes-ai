"""NL eval runner — scores all questions in questions.yaml against the live engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from nl_engine.benchmarks.grader import (
    GradeResult,
    evaluate_gate,
    grade,
    parse_gate_arg,
)
from nl_engine.benchmarks.schema import Question, load_questions
from nl_engine.context_loader import load_all
from nl_engine.engine import AnswerResponse, ClarificationResponse, ask

QUESTIONS_FILE = Path(__file__).parent / "questions.yaml"
CACHE_FILE = Path(__file__).parent / ".cache" / "responses.json"

_DEFAULT_GATE = "must-pass=80,long-tail=65"

# Question types in this set are treated as "legacy" — they were authored
# under the original eval and are kept for the long-tail / informational
# signal. The default `make eval` invocation runs only the newer dashboard
# question types; `--full` includes the legacy types too.
_LEGACY_TYPES = frozenset({
    "origination_volume", "approval_rate", "funding_rate",
    "delinquency_rate", "portfolio_balance", "product_mix",
    "channel_mix", "edge_case", "ambiguous",
})


def _cache_key(question: str, db_url: str) -> str:
    return hashlib.sha256(f"{question}|{db_url}".encode()).hexdigest()


def _load_cache() -> dict[str, dict[str, object]]:
    if CACHE_FILE.exists():
        raw: dict[str, dict[str, object]] = json.loads(CACHE_FILE.read_text())
        return raw
    return {}


def _save_cache(cache: dict[str, dict[str, object]]) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def _serialize(result: AnswerResponse | ClarificationResponse) -> dict[str, object]:
    if isinstance(result, AnswerResponse):
        return {
            "type": "answer",
            "sql": result.sql,
            "tables_used": result.tables_used,
            "rows": result.rows,
            "columns": result.columns,
        }
    return {"type": "clarification", "question": result.question}


def _deserialize(data: dict[str, object]) -> AnswerResponse | ClarificationResponse:
    if data["type"] == "answer":
        tables_raw = data.get("tables_used")
        tables: list[str] = (
            [str(t) for t in tables_raw] if isinstance(tables_raw, list) else []
        )
        rows_raw = data.get("rows")
        rows: list[dict[str, object]] = (
            [dict(r) for r in rows_raw if isinstance(r, dict)]
            if isinstance(rows_raw, list)
            else []
        )
        cols_raw = data.get("columns")
        columns: list[str] = (
            [str(c) for c in cols_raw] if isinstance(cols_raw, list) else []
        )
        return AnswerResponse(
            sql=str(data.get("sql") or ""),
            tables_used=tables,
            explanation="",
            assumptions=[],
            caveats=[],
            rows=rows,
            columns=columns,
        )
    return ClarificationResponse(question=str(data.get("question", "")))


def run(gates: dict[str, float], full: bool = False) -> int:
    db_url = os.environ["DATABASE_URL"]
    ctx = load_all()
    qf = load_questions(QUESTIONS_FILE)
    questions: list[Question] = qf.questions
    if not full:
        questions = [q for q in questions if q.question_type not in _LEGACY_TYPES]
    cache = _load_cache()

    results: list[GradeResult] = []
    for q in questions:
        key = _cache_key(q.question, db_url)
        if key in cache:
            result: AnswerResponse | ClarificationResponse = _deserialize(cache[key])
        else:
            try:
                result = ask(q.question, db_url, ctx)
            except Exception as exc:  # noqa: BLE001
                result = AnswerResponse(
                    sql="", explanation=str(exc),
                    tables_used=[], assumptions=[], caveats=[], rows=[], columns=[],
                )
            cache[key] = _serialize(result)
        results.append(grade(q, result))

    _save_cache(cache)

    exit_code, tier_summaries = evaluate_gate(results, gates)

    sys.path.insert(0, str(Path(__file__).parent))
    from report import print_report  # noqa: PLC0415

    print_report(results, tier_summaries)
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NL eval benchmark")
    parser.add_argument(
        "--gate",
        type=str,
        default=_DEFAULT_GATE,
        metavar="STR",
        help=(
            "Tier thresholds, comma-separated 'tier=PCT'. "
            f"Default: {_DEFAULT_GATE!r}. Must-pass below threshold blocks "
            "the gate; long-tail below threshold warns but does not block. "
            "Empty must-pass tier passes (does not block) — see HUG-188."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all questions; default runs only the new dashboard subset.",
    )
    args = parser.parse_args()
    try:
        gates = parse_gate_arg(args.gate)
    except ValueError as exc:
        parser.error(str(exc))
    sys.exit(run(gates, args.full))


if __name__ == "__main__":
    main()
