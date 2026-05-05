"""Schema validation for benchmark questions YAML (HUG-186)."""

from pathlib import Path

import pytest
from nl_engine.benchmarks.schema import QuestionsFile, load_questions
from pydantic import ValidationError

QUESTIONS_FILE = (
    Path(__file__).parents[1] / "benchmarks" / "questions.yaml"
)


def test_real_questions_yaml_parses() -> None:
    qf = load_questions(QUESTIONS_FILE)
    assert len(qf.questions) >= 65


def test_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError):
        QuestionsFile.model_validate({
            "questions": [{"question_type": "origination_volume"}],
        })


def test_invalid_question_type_raises() -> None:
    with pytest.raises(ValidationError) as exc:
        QuestionsFile.model_validate({
            "questions": [
                {"question": "What is foo?", "question_type": "not_a_real_type"},
            ],
        })
    assert "question_type" in str(exc.value)
