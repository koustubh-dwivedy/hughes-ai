"""Unit tests for GET /api/dashboards/executive-summary."""

from datetime import date

import pytest
from api.main import app
from api.service import dashboard_query
from api.types.executive_summary import (
    ExecutiveSummaryData,
    KpiTrendPoint,
    PastDueAgingBucket,
)
from fastapi.testclient import TestClient


def _executive_summary() -> ExecutiveSummaryData:
    return ExecutiveSummaryData(
        total_loans_balance=120_000_000.0,
        total_deposits_balance=150_000_000.0,
        loan_to_deposit_ratio=0.80,
        core_deposit_ratio=0.72,
        blended_past_due_ratio=0.012,
        monthly_loan_growth=500_000.0,
        monthly_deposit_growth=300_000.0,
        ytd_loan_growth=2_000_000.0,
        ytd_deposit_growth=1_200_000.0,
        weighted_avg_loan_rate=0.065,
        weighted_avg_deposit_rate=0.018,
        rate_spread=0.047,
        kpi_trend_13_months=[
            KpiTrendPoint(
                month=date(2026, 4, 1),
                total_loans_balance=120_000_000.0,
                total_deposits_balance=150_000_000.0,
                blended_past_due_ratio=0.012,
                rate_spread=0.047,
            )
        ],
        past_due_aging=[
            PastDueAgingBucket(bucket="30-59", balance=500_000.0, loan_count=10)
        ],
    )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.db_url = "postgresql://localhost/cubi"
        return c


def test_executive_summary_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.executive.fetch_latest_executive_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.executive_query.compose_executive_summary",
        lambda as_of, db_url: _executive_summary(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/executive-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of_date"] == "2026-04-01"
    assert body["data"]["total_loans_balance"] == 120_000_000.0
    assert body["data"]["total_deposits_balance"] == 150_000_000.0
    assert len(body["data"]["kpi_trend_13_months"]) == 1
    assert len(body["data"]["past_due_aging"]) == 1


def test_executive_summary_cache_control(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.executive.fetch_latest_executive_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.executive_query.compose_executive_summary",
        lambda as_of, db_url: _executive_summary(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/executive-summary")
    assert resp.headers["cache-control"] == "max-age=300, public"


def test_executive_summary_cache_hit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    dashboard_query.cache_clear()
    call_count = 0

    def _compose(as_of: date, db_url: str) -> ExecutiveSummaryData:
        nonlocal call_count
        call_count += 1
        return _executive_summary()

    monkeypatch.setattr(
        "api.service.executive_query.compose_executive_summary", _compose
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    client.get("/api/dashboards/executive-summary?as_of_date=2026-03-01")
    client.get("/api/dashboards/executive-summary?as_of_date=2026-03-01")
    assert call_count == 1


def test_executive_summary_explicit_as_of(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: dict[str, object] = {}

    def _compose(as_of: date, db_url: str) -> ExecutiveSummaryData:
        received["as_of"] = as_of
        return _executive_summary()

    monkeypatch.setattr(
        "api.service.executive_query.compose_executive_summary", _compose
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get(
        "/api/dashboards/executive-summary?as_of_date=2026-02-01"
    )
    assert resp.status_code == 200
    assert received["as_of"] == date(2026, 2, 1)
