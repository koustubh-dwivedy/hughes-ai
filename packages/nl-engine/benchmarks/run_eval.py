"""NL eval runner — scores all questions in questions.yaml against the live engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from nl_engine.benchmarks.schema import Question, load_questions
from nl_engine.context_loader import load_all
from nl_engine.engine import AnswerResponse, ClarificationResponse, ask

QUESTIONS_FILE = Path(__file__).parent / "questions.yaml"
CACHE_FILE = Path(__file__).parent / ".cache" / "responses.json"
PASS_THRESHOLD = 0.5

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
        return {"type": "answer", "sql": result.sql, "tables_used": result.tables_used}
    return {"type": "clarification", "question": result.question}


def _deserialize(data: dict[str, object]) -> AnswerResponse | ClarificationResponse:
    if data["type"] == "answer":
        tables_raw = data.get("tables_used")
        tables: list[str] = (
            [str(t) for t in tables_raw] if isinstance(tables_raw, list) else []
        )
        return AnswerResponse(
            sql=str(data.get("sql") or ""),
            tables_used=tables,
            explanation="",
            assumptions=[],
            caveats=[],
            rows=[],
            columns=[],
        )
    return ClarificationResponse(question=str(data.get("question", "")))


def _table_jaccard(
    expected: set[str], actual: set[str]
) -> float:
    if not expected:
        return 1.0
    union = expected | actual
    return len(expected & actual) / len(union) if union else 1.0


def _keyword_frac(expected: list[str], sql: str) -> float:
    if not expected:
        return 1.0
    sql_upper = sql.upper()
    matched = sum(1 for kw in expected if kw.upper() in sql_upper)
    return matched / len(expected)


def _score(
    q: Question,
    result: AnswerResponse | ClarificationResponse,
) -> dict[str, object]:
    qtype = q.question_type
    expected_tables: set[str] = set(q.expected_tables)
    expected_keywords: list[str] = list(q.expected_keywords)

    if qtype == "ambiguous":
        correct = isinstance(result, ClarificationResponse)
        return {
            "question": q.question,
            "question_type": qtype,
            "correct": correct,
            "sql_valid": None,
            "table_jaccard": None,
            "keyword_frac": None,
        }

    if isinstance(result, ClarificationResponse):
        return {
            "question": q.question,
            "question_type": qtype,
            "correct": False,
            "sql_valid": False,
            "table_jaccard": 0.0,
            "keyword_frac": 0.0,
        }

    sql = result.sql or ""
    sql_valid = bool(sql.strip())
    jaccard = _table_jaccard(expected_tables, set(result.tables_used or []))
    kw_frac = _keyword_frac(expected_keywords, sql)
    correct = sql_valid and jaccard >= PASS_THRESHOLD and kw_frac >= PASS_THRESHOLD
    return {
        "question": q.question,
        "question_type": qtype,
        "correct": correct,
        "sql_valid": sql_valid,
        "table_jaccard": round(jaccard, 3),
        "keyword_frac": round(kw_frac, 3),
    }


def run(fail_under: float, full: bool = False) -> int:
    db_url = os.environ["DATABASE_URL"]
    ctx = load_all()
    qf = load_questions(QUESTIONS_FILE)
    questions: list[Question] = qf.questions
    if not full:
        questions = [q for q in questions if q.question_type not in _LEGACY_TYPES]
    cache = _load_cache()

    results: list[dict[str, object]] = []
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
        results.append(_score(q, result))

    _save_cache(cache)

    sys.path.insert(0, str(Path(__file__).parent))
    from report import print_report  # noqa: PLC0415

    accuracy = print_report(results, fail_under)

    if full:
        legacy = [r for r in results if r["question_type"] in _LEGACY_TYPES]
        if legacy:
            leg_correct = sum(1 for r in legacy if r["correct"])
            leg_acc = leg_correct / len(legacy) * 100
            leg_status = "PASS" if leg_acc >= fail_under else "FAIL"
            print(  # noqa: T201
                f"Legacy (50q): {leg_correct}/{len(legacy)}"
                f" ({leg_acc:.1f}%) — {leg_status}"
            )
            if leg_acc < fail_under:
                return 1

    return 0 if accuracy >= fail_under else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NL eval benchmark")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=85.0,
        metavar="N",
        help="Exit 1 if accuracy is below N%% (default: 85)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all 70 questions; default runs only the 20 new dashboard questions",
    )
    args = parser.parse_args()
    sys.exit(run(args.fail_under, args.full))


if __name__ == "__main__":
    main()
