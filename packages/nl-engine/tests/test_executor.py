"""Unit tests for executor.py — psycopg monkeypatched."""

from unittest.mock import MagicMock, patch

import psycopg
import pytest
from nl_engine.executor import execute_sql


def _make_mock_conn(
    rows: list[tuple[object, ...]], col_names: list[str]
) -> MagicMock:
    desc = []
    for n in col_names:
        m = MagicMock()
        m.name = n
        desc.append(m)

    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.description = desc
    cursor.fetchall.return_value = rows

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


def test_execute_returns_rows() -> None:
    raw_rows: list[tuple[object, ...]] = [("abc", "2024-01-01"), ("def", "2024-02-01")]
    col_names = ["loan_id", "funded_at"]
    mock_conn = _make_mock_conn(raw_rows, col_names)

    with patch("nl_engine.executor.psycopg.connect", return_value=mock_conn):
        rows, columns = execute_sql(
            "SELECT loan_id, funded_at FROM fct_loan_originations", "dburl"
        )

    assert columns == col_names
    assert rows == [
        {"loan_id": "abc", "funded_at": "2024-01-01"},
        {"loan_id": "def", "funded_at": "2024-02-01"},
    ]


def test_statement_timeout_set() -> None:
    mock_conn = _make_mock_conn([], ["loan_id"])

    with patch("nl_engine.executor.psycopg.connect", return_value=mock_conn):
        execute_sql("SELECT loan_id FROM fct_loan_originations", "dburl")

    mock_conn.execute.assert_called_once_with("SET statement_timeout = 30000")


def test_connect_error_propagates() -> None:
    with (
        patch(
            "nl_engine.executor.psycopg.connect",
            side_effect=psycopg.OperationalError("connection refused"),
        ),
        pytest.raises(psycopg.OperationalError, match="connection refused"),
    ):
        execute_sql("SELECT 1", "bad-url")
