"""Unit tests for dashboard service: date helpers and TTL cache."""

from datetime import date

import pytest
from api.service import dashboard_query


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    dashboard_query.cache_clear()


# ── Date helpers ──────────────────────────────────────────────────────────────


def test_mtd_range() -> None:
    start, end = dashboard_query.mtd_range(date(2026, 4, 28))
    assert start == date(2026, 4, 1)
    assert end == date(2026, 4, 28)


def test_ytd_range() -> None:
    start, end = dashboard_query.ytd_range(date(2026, 4, 28))
    assert start == date(2026, 1, 1)
    assert end == date(2026, 4, 28)


def test_prior_ytd_range() -> None:
    start, end = dashboard_query.prior_ytd_range(date(2026, 4, 28))
    assert start == date(2025, 1, 1)
    assert end == date(2025, 4, 28)


# ── Cache ─────────────────────────────────────────────────────────────────────


def test_cache_hit_within_ttl() -> None:
    dashboard_query.cache_set("deposit-portfolio", "2026-04-28", {"total": 1})
    result = dashboard_query.cache_get("deposit-portfolio", "2026-04-28")
    assert result == {"total": 1}


def test_cache_miss_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    base = dashboard_query._monotonic()
    dashboard_query.cache_set("deposit-portfolio", "2026-04-28", {"total": 1})

    monkeypatch.setattr(
        dashboard_query, "_monotonic", lambda: base + dashboard_query._TTL + 1
    )
    result = dashboard_query.cache_get("deposit-portfolio", "2026-04-28")
    assert result is None


def test_cache_miss_for_unknown_key() -> None:
    assert dashboard_query.cache_get("unknown", "2026-04-28") is None


def test_cache_different_keys_independent() -> None:
    dashboard_query.cache_set("ep-a", "2026-04-01", "val-a")
    dashboard_query.cache_set("ep-b", "2026-04-01", "val-b")
    assert dashboard_query.cache_get("ep-a", "2026-04-01") == "val-a"
    assert dashboard_query.cache_get("ep-b", "2026-04-01") == "val-b"
