"""NL eval runner — scores all questions in questions.yaml against the live engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml
from nl_engine.context_loader import load_all
from nl_engine.engine import AnswerResponse, ClarificationResponse, ask

QUESTIONS_FILE = Path(__file__).parent / "questions.yaml"
CACHE_FILE = Path(__file__).parent / ".cache" / "responses.json"
PASS_THRESHOLD = 0.5


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


def _score(
    q: dict[str, object],
    result: AnswerResponse | ClarificationResponse,
) -> dict[str, object]:
    qtype = str(q["question_type"])
    tables_raw = q.get("expected_tables")
    keywords_raw = q.get("expected_keywords")
    expected_tables: set[str] = (
        {str(t) for t in tables_raw} if isinstance(tables_raw, list) else set()
    )
    expected_keywords: list[str] = (
        [str(k) for k in keywords_raw] if isinstance(keywords_raw, list) else []
    )

    if qtype == "ambiguous":
        correct = isinstance(result, ClarificationResponse)
        return {
            "question": q["question"],
            "question_type": qtype,
            "correct": correct,
            "sql_valid": None,
            "table_jaccard": None,
            "keyword_frac": None,
        }

    if isinstance(result, ClarificationResponse):
        return {
            "question": q["question"],
            "question_type": qtype,
            "correct": False,
            "sql_valid": False,
            "table_jaccard": 0.0,
            "keyword_frac": 0.0,
        }

    sql = result.sql or ""
    sql_valid = bool(sql.strip())

    actual_tables: set[str] = set(result.tables_used or [])
    if expected_tables:
        union = expected_tables | actual_tables
        jaccard = len(expected_tables & actual_tables) / len(union) if union else 1.0
    else:
        jaccard = 1.0

    sql_upper = sql.upper()
    if expected_keywords:
        matched = sum(1 for kw in expected_keywords if kw.upper() in sql_upper)
        keyword_frac = matched / len(expected_keywords)
    else:
        keyword_frac = 1.0

    correct = sql_valid and jaccard >= PASS_THRESHOLD and keyword_frac >= PASS_THRESHOLD
    return {
        "question": q["question"],
        "question_type": qtype,
        "correct": correct,
        "sql_valid": sql_valid,
        "table_jaccard": round(jaccard, 3),
        "keyword_frac": round(keyword_frac, 3),
    }


def run(fail_under: float) -> int:
    db_url = os.environ["DATABASE_URL"]
    ctx = load_all()
    raw = yaml.safe_load(QUESTIONS_FILE.read_text())
    questions: list[dict[str, object]] = raw["questions"]
    cache = _load_cache()

    results: list[dict[str, object]] = []
    for q in questions:
        key = _cache_key(str(q["question"]), db_url)
        if key in cache:
            result = _deserialize(cache[key])
        else:
            result = ask(str(q["question"]), db_url, ctx)
            cache[key] = _serialize(result)
        results.append(_score(q, result))

    _save_cache(cache)

    sys.path.insert(0, str(Path(__file__).parent))
    from report import print_report  # noqa: PLC0415

    accuracy = print_report(results, fail_under)
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
    args = parser.parse_args()
    sys.exit(run(args.fail_under))


if __name__ == "__main__":
    main()
