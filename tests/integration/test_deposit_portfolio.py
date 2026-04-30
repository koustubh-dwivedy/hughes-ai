"""Integration test: deposit-portfolio repo + service against seeded DB."""

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


def test_fetch_latest_deposit_month(db_url: str) -> None:
    as_of = repo.fetch_latest_deposit_month(db_url)
    assert isinstance(as_of, date)


def test_deposit_portfolio_shape(db_url: str) -> None:
    as_of = repo.fetch_latest_deposit_month(db_url)
    data = svc.compose_deposit_portfolio(as_of, db_url)

    assert data.total_deposits > 0
    assert data.account_count > 0
    assert data.avg_balance_per_customer > 0
    assert len(data.top_25_deposits) > 0
    assert len(data.deposits_by_branch) > 0
    assert len(data.deposit_mix) > 0
    assert len(data.change_by_product) > 0
    assert data.new_vs_closed_accounts.opened.count >= 0
    assert data.new_vs_closed_accounts.closed.count >= 0

    total_mix = sum(p.balance for p in data.deposit_mix)
    assert abs(total_mix - data.total_deposits) < 1.0
