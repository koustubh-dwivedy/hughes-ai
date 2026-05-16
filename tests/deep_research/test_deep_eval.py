"""Unit tests for the deep-research eval harness (HUG-248).

Validates the yaml loader, dry-run wiring, and grader JSON-extraction
helper without invoking an LLM or DB.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_yaml_loads_14_questions() -> None:
    import deep_eval  # type: ignore[import-not-found]

    questions = deep_eval._load_questions()
    assert len(questions) == 14
    for q in questions:
        assert "id" in q
        assert "question" in q
        assert "rubric" in q
        assert q["rubric"], f"empty rubric for {q['id']}"


def test_dry_run_produces_skipped_artefact() -> None:
    import deep_eval  # type: ignore[import-not-found]

    q = {"id": "dr-test", "question": "noop", "rubric": ["x"]}
    artefact = deep_eval._run_one_question(q, db_url="", dry_run=True)
    assert artefact["id"] == "dr-test"
    assert artefact["skipped"] is True


def test_safe_parse_grader_extracts_embedded_json() -> None:
    import deep_eval  # type: ignore[import-not-found]

    raw = (
        'Sure! Here is my verdict:\n'
        '{"per_criterion": [true, false], "overall": false, '
        '"rationale": "missed criterion 2"}\n'
        'Hope that helps.'
    )
    parsed = deep_eval._safe_parse_grader(raw)
    assert parsed["overall"] is False
    assert parsed["per_criterion"] == [True, False]
    assert "missed" in parsed["rationale"]


def test_safe_parse_grader_handles_garbage() -> None:
    import deep_eval  # type: ignore[import-not-found]

    parsed = deep_eval._safe_parse_grader("no json here at all")
    assert parsed["overall"] is False
    assert "JSON" in parsed["rationale"] or "no JSON" in parsed["rationale"]


def test_extract_final_answer_returns_none_on_empty() -> None:
    import deep_eval  # type: ignore[import-not-found]

    assert deep_eval._extract_final_answer([]) is None
