"""Integration test: past-due repo + service against seeded DB."""

import os
from datetime import date

import pytest
from api.repo import dashboards as repo
from api.service import dashboard_query as svc


@pytest.fixture
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


def test_fetch_latest_delinquency_month(db_url: str) -> None:
    as_of = repo.fetch_latest_delinquency_month(db_url)
    assert isinstance(as_of, date)


def test_past_due_shape(db_url: str) -> None:
    as_of = repo.fetch_latest_delinquency_month(db_url)
    data = svc.compose_past_due(as_of, db_url)

    assert data.past_due_total >= 0
    assert data.nonaccrual_total >= 0
    assert data.watchlist_count >= 0
    assert data.nonperforming_balance >= 0
    assert 1 <= len(data.delinquency_trend_13_months) <= 13
    assert len(data.past_due_ratio_trend) >= 1

    for pt in data.past_due_ratio_trend:
        assert 0.0 <= pt.ratio <= 1.0

    for month in data.delinquency_trend_13_months:
        assert month.bucket_30_59 >= 0
        assert month.bucket_60_89 >= 0
        assert month.bucket_90_plus >= 0
