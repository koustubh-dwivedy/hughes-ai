"""Unit tests for GET /api/dashboards/officer-branch."""

from datetime import date

import pytest
from api.main import app
from api.service import dashboard_query
from api.types.officer_branch import (
    ComboBalanceRate,
    LoanMixItem,
    OfficerBranchData,
    SingleLoanCount,
    TopBorrower,
    WaterfallStep,
)
from fastapi.testclient import TestClient


def _officer_branch() -> OfficerBranchData:
    return OfficerBranchData(
        total_loans=10_000_000.0,
        account_count=250,
        avg_loan_balance=40_000.0,
        top_25_borrowers=[
            TopBorrower(member_name="John Smith", balance=200_000.0, share_pct=2.0)
        ],
        loan_mix_donut=[
            LoanMixItem(product="Auto", balance=4_000_000.0, share_pct=40.0)
        ],
        change_by_type_waterfall=[
            WaterfallStep(product="Auto", delta=50_000.0)
        ],
        single_loan_customers_by_type=[
            SingleLoanCount(product="Auto", count=80)
        ],
        combo_balance_rate=[
            ComboBalanceRate(
                product="Auto", balance=4_000_000.0, weighted_avg_rate=0.065
            )
        ],
    )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.db_url = "postgresql://localhost/cubi"
        return c


def test_officer_branch_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.loans.fetch_latest_loans_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_officer_branch",
        lambda as_of, db_url, branch_id=None, officer_id=None: _officer_branch(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/officer-branch")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of_date"] == "2026-04-01"
    assert body["data"]["total_loans"] == 10_000_000.0
    assert body["data"]["account_count"] == 250
    assert len(body["data"]["top_25_borrowers"]) == 1
    assert body["data"]["top_25_borrowers"][0]["member_name"] == "John Smith"


def test_officer_branch_cache_control(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.loans.fetch_latest_loans_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_officer_branch",
        lambda as_of, db_url, branch_id=None, officer_id=None: _officer_branch(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/officer-branch")
    assert resp.headers["cache-control"] == "max-age=300, public"


def test_officer_branch_cache_hit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    dashboard_query.cache_clear()
    call_count = 0

    def _compose(
        as_of: date,
        db_url: str,
        branch_id: int | None = None,
        officer_id: str | None = None,
    ) -> OfficerBranchData:
        nonlocal call_count
        call_count += 1
        return _officer_branch()

    monkeypatch.setattr("api.service.dashboard_query.compose_officer_branch", _compose)
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    client.get("/api/dashboards/officer-branch?as_of_date=2026-03-01")
    client.get("/api/dashboards/officer-branch?as_of_date=2026-03-01")
    assert call_count == 1


def test_officer_branch_with_filters(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: dict[str, object] = {}

    def _compose(
        as_of: date,
        db_url: str,
        branch_id: int | None = None,
        officer_id: str | None = None,
    ) -> OfficerBranchData:
        received["branch_id"] = branch_id
        received["officer_id"] = officer_id
        return _officer_branch()

    monkeypatch.setattr("api.service.dashboard_query.compose_officer_branch", _compose)
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get(
        "/api/dashboards/officer-branch?as_of_date=2026-02-01&branch_id=3&officer_id=abc"
    )
    assert resp.status_code == 200
    assert received["branch_id"] == 3
    assert received["officer_id"] == "abc"
