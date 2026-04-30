"""Unit tests for GET /api/dashboards/deposit-portfolio."""

from datetime import date

import pytest
from api.main import app
from api.service import dashboard_query
from api.types.deposit_portfolio import (
    AccountActivity,
    BranchBalance,
    DepositPortfolioData,
    NewVsClosed,
    ProductBalance,
    ProductDelta,
    TopDeposit,
)
from fastapi.testclient import TestClient


def _portfolio() -> DepositPortfolioData:
    return DepositPortfolioData(
        total_deposits=1_000_000.0,
        mtd_change=5_000.0,
        ytd_change=20_000.0,
        avg_balance_per_customer=2_500.0,
        account_count=400,
        top_25_deposits=[
            TopDeposit(member_name="Alice Smith", balance=50_000.0, share_pct=5.0)
        ],
        deposits_by_branch=[BranchBalance(branch_name="Alpha", balance=200_000.0)],
        deposit_mix=[
            ProductBalance(product="Savings", balance=400_000.0, share_pct=40.0)
        ],
        change_by_product=[ProductDelta(product="Savings", delta=10_000.0)],
        new_vs_closed_accounts=NewVsClosed(
            opened=AccountActivity(count=10, amount=25_000.0),
            closed=AccountActivity(count=3, amount=7_500.0),
        ),
    )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.db_url = "postgresql://localhost/cubi"
        return c


def test_deposit_portfolio_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.dashboards.fetch_latest_deposit_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_deposit_portfolio",
        lambda as_of, db_url: _portfolio(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/deposit-portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of_date"] == "2026-04-01"
    assert body["data"]["total_deposits"] == 1_000_000.0
    assert body["data"]["account_count"] == 400
    assert len(body["data"]["top_25_deposits"]) == 1
    assert body["data"]["top_25_deposits"][0]["member_name"] == "Alice Smith"


def test_deposit_portfolio_cache_control(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.dashboards.fetch_latest_deposit_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_deposit_portfolio",
        lambda as_of, db_url: _portfolio(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/deposit-portfolio")
    assert resp.headers["cache-control"] == "max-age=300, public"


def test_deposit_portfolio_cache_hit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    dashboard_query.cache_clear()
    call_count = 0

    def _compose(as_of: date, db_url: str) -> DepositPortfolioData:
        nonlocal call_count
        call_count += 1
        return _portfolio()

    monkeypatch.setattr(
        "api.repo.dashboards.fetch_latest_deposit_month",
        lambda db_url: date(2026, 3, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_deposit_portfolio", _compose
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    client.get("/api/dashboards/deposit-portfolio?as_of_date=2026-03-01")
    client.get("/api/dashboards/deposit-portfolio?as_of_date=2026-03-01")
    assert call_count == 1  # second request served from cache


def test_deposit_portfolio_explicit_date(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_deposit_portfolio",
        lambda as_of, db_url: _portfolio(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/deposit-portfolio?as_of_date=2026-02-01")
    assert resp.status_code == 200
    assert resp.json()["as_of_date"] == "2026-02-01"
