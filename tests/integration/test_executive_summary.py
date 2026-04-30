"""Integration test: executive-summary repo + service against seeded DB."""

import os
from datetime import date

import pytest
from api.repo import executive as repo_exec
from api.service import executive_query as svc


@pytest.fixture
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


def test_fetch_latest_executive_month(db_url: str) -> None:
    as_of = repo_exec.fetch_latest_executive_month(db_url)
    assert isinstance(as_of, date)


def test_executive_summary_shape(db_url: str) -> None:
    as_of = repo_exec.fetch_latest_executive_month(db_url)
    data = svc.compose_executive_summary(as_of, db_url)

    assert data.total_loans_balance > 0
    assert data.total_deposits_balance > 0
    assert 0 < data.loan_to_deposit_ratio < 2
    assert len(data.kpi_trend_13_months) > 0
    assert len(data.past_due_aging) > 0


def test_executive_summary_ytd_growth_finite(db_url: str) -> None:
    as_of = repo_exec.fetch_latest_executive_month(db_url)
    data = svc.compose_executive_summary(as_of, db_url)
    assert isinstance(data.ytd_loan_growth, float)
    assert isinstance(data.ytd_deposit_growth, float)
