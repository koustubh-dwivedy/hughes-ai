"""Tests for HUG-262 — strip the mf CLI's 'new version available' warning.

The mf CLI prints a banner to stdout on every invocation. It pollutes our
captured stdout and showed up in `mf_query.attempt_failed` error strings
on 2026-05-18. _strip_update_warning removes it.
"""

from __future__ import annotations

from nl_engine.repo.metricflow import _strip_update_warning


def test_strip_preserves_clean_output() -> None:
    clean = "metric_a\nmetric_b\n• metric_c\n"
    assert _strip_update_warning(clean) == clean


def test_strip_removes_full_warning_block() -> None:
    polluted = (
        "‼️ Warning: A new version of the MetricFlow CLI is available.\n"
        "💡 Please update to version 0.13.0, released 2026-05-12 by running:\n"
        "\t$ pip install --upgrade dbt-metricflow\n"
        "\n"
        "• delinquency_rate: a, b, c\n"
        "• portfolio_balance: x, y, z\n"
    )
    cleaned = _strip_update_warning(polluted)
    assert "Warning" not in cleaned
    assert "Please update" not in cleaned
    assert "pip install" not in cleaned
    assert "• delinquency_rate: a, b, c" in cleaned
    assert "• portfolio_balance: x, y, z" in cleaned


def test_strip_preserves_lines_after_warning_block() -> None:
    """Real-world ordering: warning at top, then mf's actual output."""
    polluted = (
        "‼️ Warning: blah blah\n"
        "💡 Please update to 0.13.0\n"
        "\t$ pip install --upgrade dbt-metricflow\n"
        "\n"
        "row1,col2,col3\n"
        "1,2,3\n"
    )
    cleaned = _strip_update_warning(polluted)
    assert cleaned == "row1,col2,col3\n1,2,3\n"


def test_strip_handles_warning_without_pip_line() -> None:
    """Defensive: if the upstream format changes and drops the pip line,
    we still drop the headline."""
    polluted = (
        "‼️ Warning: A new version of the MetricFlow CLI is available.\n"
        "real output here\n"
    )
    cleaned = _strip_update_warning(polluted)
    assert "Warning" not in cleaned
    assert "real output here\n" in cleaned


def test_strip_idempotent_when_no_warning_present() -> None:
    text = "no banner here\njust data\n"
    assert _strip_update_warning(text) == text
    assert _strip_update_warning(_strip_update_warning(text)) == text
