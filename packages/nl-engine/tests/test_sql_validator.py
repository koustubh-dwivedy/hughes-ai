"""Unit tests for sql_validator.py — pure AST checks, no mocks needed."""

import pytest
from nl_engine.context_loader import Column, Table
from nl_engine.context_selector import SelectedContext
from nl_engine.sql_validator import SQLValidationError, validate_sql


def _ctx(*table_names: str, extra_cols: list[str] | None = None) -> SelectedContext:
    cols = [
        Column(name="loan_id", type="TEXT", description="", example=""),
        Column(name="funded_at", type="TIMESTAMPTZ", description="", example=""),
        Column(name="loan_status", type="TEXT", description="", example=""),
    ]
    if extra_cols:
        cols += [
            Column(name=c, type="TEXT", description="", example="")
            for c in extra_cols
        ]
    tables = [Table(name=n, description="", columns=cols) for n in table_names]
    return SelectedContext(
        relevant_tables=tables,
        relevant_metrics=[],
        relevant_columns=cols,
        relevant_examples=[],
    )


def test_valid_select_passes() -> None:
    validate_sql(
        "SELECT loan_id FROM fct_loan_originations", _ctx("fct_loan_originations")
    )


def test_star_select_passes() -> None:
    validate_sql(
        "SELECT * FROM fct_loan_originations", _ctx("fct_loan_originations")
    )


def test_drop_rejected() -> None:
    with pytest.raises(SQLValidationError, match="Only SELECT"):
        validate_sql(
            "DROP TABLE fct_loan_originations", _ctx("fct_loan_originations")
        )


def test_insert_rejected() -> None:
    with pytest.raises(SQLValidationError, match="Only SELECT"):
        validate_sql(
            "INSERT INTO fct_loan_originations (loan_id) VALUES ('x')",
            _ctx("fct_loan_originations"),
        )


def test_update_rejected() -> None:
    with pytest.raises(SQLValidationError, match="Only SELECT"):
        validate_sql(
            "UPDATE fct_loan_originations SET loan_id = 'x'",
            _ctx("fct_loan_originations"),
        )


def test_unknown_table_rejected() -> None:
    with pytest.raises(SQLValidationError, match="not in the allowlist"):
        validate_sql("SELECT id FROM users", _ctx("fct_loan_originations"))


def test_unknown_column_rejected() -> None:
    with pytest.raises(SQLValidationError, match="not in the allowlist"):
        validate_sql(
            "SELECT secret FROM fct_loan_originations",
            _ctx("fct_loan_originations"),
        )


def test_parse_error_raises() -> None:
    with pytest.raises(SQLValidationError, match="Parse error"):
        validate_sql("NOT VALID SQL %%%", _ctx("fct_loan_originations"))
