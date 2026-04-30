"""Integration test: officer-branch repo + service against seeded DB."""

import os
from datetime import date

import pytest
from api.repo import dashboards as repo
from api.repo import loans as repo_loans
from api.service import dashboard_query as svc


@pytest.fixture
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


def test_fetch_latest_loans_month(db_url: str) -> None:
    as_of = repo_loans.fetch_latest_loans_month(db_url)
    assert isinstance(as_of, date)


def test_officer_branch_shape(db_url: str) -> None:
    as_of = repo_loans.fetch_latest_loans_month(db_url)
    data = svc.compose_officer_branch(as_of, db_url)

    assert data.total_loans > 0
    assert data.account_count > 0
    assert data.avg_loan_balance > 0
    assert len(data.top_25_borrowers) == 25
    assert len(data.loan_mix_donut) > 0
    assert len(data.change_by_type_waterfall) > 0
    assert len(data.single_loan_customers_by_type) > 0
    assert len(data.combo_balance_rate) > 0

    total_share = sum(p.share_pct for p in data.loan_mix_donut)
    assert abs(total_share - 100.0) < 0.1


def test_officer_branch_branch_filter(db_url: str) -> None:
    as_of = repo_loans.fetch_latest_loans_month(db_url)
    all_data = svc.compose_officer_branch(as_of, db_url)

    branch_id = repo.fetch_mart_rows(
        "SELECT MIN(branch_id) AS b FROM fct_loans_monthly WHERE as_of_month = %s",
        (as_of,),
        db_url,
    )[0]["b"]
    filtered = svc.compose_officer_branch(as_of, db_url, branch_id=int(branch_id))

    assert filtered.total_loans <= all_data.total_loans
    assert filtered.account_count <= all_data.account_count
