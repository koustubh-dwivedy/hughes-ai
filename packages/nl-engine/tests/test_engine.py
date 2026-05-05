"""Unit tests for nl_engine.engine — Groq client mocked throughout (HUG-183).

The engine's `_call_llm` returns a 3-tuple `(parsed_dict, token_count, model_name)`;
mocks must respect that shape. The full pipeline tests stub `_call_llm` with a
lambda that returns the tuple, NOT just the dict.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from nl_engine.context_loader import AllContext, Column, Example, Metric, Rule, Table
from nl_engine.context_selector import SelectedContext
from nl_engine.engine import AnswerResponse, ClarificationResponse, _call_llm, ask
from nl_engine.sql_validator import SQLValidationError

_VALID_SQL = "SELECT loan_id FROM fct_loan_originations"

_VALID_LLM_RESPONSE: dict[str, object] = {
    "sql": _VALID_SQL,
    "explanation": "Returns all loan IDs.",
    "tables_used": ["fct_loan_originations"],
    "assumptions": [],
    "caveats": ["Only funded loans are included."],
}

_VALID_LLM_TUPLE = (_VALID_LLM_RESPONSE, 100, "qwen/qwen3-32b")


def _make_ctx() -> AllContext:
    col = Column(name="loan_id", type="TEXT", description="Loan ID", example="abc")
    col2 = Column(
        name="funded_at",
        type="TIMESTAMPTZ",
        description="Funded at",
        example="2024-01-01",
    )
    col3 = Column(
        name="loan_status", type="TEXT", description="Status", example="current"
    )
    table = Table(
        name="fct_loan_originations",
        description="One row per funded loan.",
        columns=[col, col2, col3],
    )
    metric = Metric(
        name="origination_volume",
        label="Origination Volume",
        description="Count of funded loans",
        formula_plain_english="Count funded_at rows in period",
        caveats="Funded only.",
        related_questions=["How many loans?"],
    )
    example = Example(
        question="How many originations last month?",
        sql="SELECT COUNT(*) FROM fct_loan_originations",
        notes="",
    )
    rule = Rule(id="r1", rule="Use funded_at", rationale="Industry standard")
    return AllContext(
        tables=[table], metrics=[metric], rules=[rule], examples=[example]
    )


def test_ask_returns_answer_response(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_ctx()
    mock_rows: list[dict[str, object]] = [{"loan_id": "abc"}]

    monkeypatch.setattr(
        "nl_engine.engine._call_llm", lambda *_a, **_kw: _VALID_LLM_TUPLE
    )
    monkeypatch.setattr(
        "nl_engine.engine.execute_sql",
        lambda *_a, **_kw: (mock_rows, ["loan_id"]),
    )

    result = ask("How many originations?", "postgresql://localhost/cubi", ctx)

    assert isinstance(result, AnswerResponse)
    assert "SELECT" in result.sql.upper()
    assert result.rows == mock_rows


def test_ask_unknown_topic_returns_clarification() -> None:
    ctx = _make_ctx()
    result = ask("Tell me about the weather", "postgresql://localhost/cubi", ctx)
    assert isinstance(result, ClarificationResponse)
    assert result.question


def test_ask_sql_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_ctx()
    validated_sqls: list[str] = []

    def capture_validate(sql: str, sel_ctx: SelectedContext) -> None:
        validated_sqls.append(sql)

    monkeypatch.setattr(
        "nl_engine.engine._call_llm", lambda *_a, **_kw: _VALID_LLM_TUPLE
    )
    monkeypatch.setattr("nl_engine.engine.validate_sql", capture_validate)
    monkeypatch.setattr(
        "nl_engine.engine.execute_sql", lambda *_a, **_kw: ([], [])
    )

    ask("How many originations?", "postgresql://localhost/cubi", ctx)

    assert len(validated_sqls) == 1
    assert validated_sqls[0] == _VALID_SQL


def test_invalid_llm_sql_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_ctx()
    dangerous_response = dict(
        _VALID_LLM_RESPONSE, sql="DROP TABLE fct_loan_originations"
    )
    dangerous_tuple = (dangerous_response, 50, "qwen/qwen3-32b")
    execute_called = False

    def fake_execute(
        *_a: object, **_kw: object
    ) -> tuple[list[dict[str, object]], list[str]]:
        nonlocal execute_called
        execute_called = True
        return [], []

    monkeypatch.setattr(
        "nl_engine.engine._call_llm", lambda *_a, **_kw: dangerous_tuple
    )
    monkeypatch.setattr("nl_engine.engine.execute_sql", fake_execute)

    with pytest.raises(SQLValidationError):
        ask("How many originations?", "postgresql://localhost/cubi", ctx)

    assert not execute_called


def test_llm_json_parse_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bad JSON from Groq surfaces as JSONDecodeError, not silently corrupted."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "not-json{{"
    fake_response.usage = None
    fake_response.model = "qwen/qwen3-32b"
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response
    with (
        patch("nl_engine.engine.Groq", return_value=fake_client),
        patch("nl_engine.engine.ChatCompletion", new=type(fake_response)),
        pytest.raises(json.JSONDecodeError),
    ):
        _call_llm("system", "question")
