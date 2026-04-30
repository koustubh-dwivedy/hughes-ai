"""Unit tests for GET /api/dashboards/past-due."""

from datetime import date

import pytest
from api.main import app
from api.service import dashboard_query
from api.types.past_due import (
    DelinquencyTrendMonth,
    OfficerDelinquency,
    PastDueData,
    PastDueRatioPoint,
)
from fastapi.testclient import TestClient


def _past_due() -> PastDueData:
    return PastDueData(
        past_due_total=500_000.0,
        past_due_total_delta=-10_000.0,
        nonaccrual_total=120_000.0,
        nonaccrual_total_delta=0.0,
        watchlist_count=5,
        watchlist_count_delta=1,
        nonperforming_balance=200_000.0,
        nonperforming_balance_delta=-5_000.0,
        past_due_by_officer=[
            OfficerDelinquency(officer_name="Jane Doe", balance=300_000.0, count=8)
        ],
        delinquency_trend_13_months=[
            DelinquencyTrendMonth(
                month=date(2026, 4, 1),
                bucket_30_59=100_000.0,
                bucket_60_89=80_000.0,
                bucket_90_plus=120_000.0,
            )
        ],
        past_due_ratio_trend=[
            PastDueRatioPoint(month=date(2026, 4, 1), ratio=0.05)
        ],
    )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.db_url = "postgresql://localhost/cubi"
        return c


def test_past_due_200(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.repo.dashboards.fetch_latest_delinquency_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_past_due",
        lambda as_of, db_url: _past_due(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/past-due")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of_date"] == "2026-04-01"
    assert body["data"]["past_due_total"] == 500_000.0
    assert body["data"]["watchlist_count"] == 5
    assert len(body["data"]["past_due_by_officer"]) == 1
    assert body["data"]["past_due_by_officer"][0]["officer_name"] == "Jane Doe"


def test_past_due_cache_control(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.dashboards.fetch_latest_delinquency_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_past_due",
        lambda as_of, db_url: _past_due(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/past-due")
    assert resp.headers["cache-control"] == "max-age=300, public"


def test_past_due_cache_hit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    dashboard_query.cache_clear()
    call_count = 0

    def _compose(as_of: date, db_url: str) -> PastDueData:
        nonlocal call_count
        call_count += 1
        return _past_due()

    monkeypatch.setattr(
        "api.repo.dashboards.fetch_latest_delinquency_month",
        lambda db_url: date(2026, 3, 1),
    )
    monkeypatch.setattr("api.service.dashboard_query.compose_past_due", _compose)
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    client.get("/api/dashboards/past-due?as_of_date=2026-03-01")
    client.get("/api/dashboards/past-due?as_of_date=2026-03-01")
    assert call_count == 1


def test_past_due_explicit_date(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_past_due",
        lambda as_of, db_url: _past_due(),
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/api/dashboards/past-due?as_of_date=2026-02-01")
    assert resp.status_code == 200
    assert resp.json()["as_of_date"] == "2026-02-01"
