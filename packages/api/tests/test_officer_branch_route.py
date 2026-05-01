"""Unit tests for GET /dashboards/officer-branch."""

from datetime import date

import pytest
from api.main import app
from api.service import dashboard_query
from api.types.officer_branch import (
    ComboBalanceRate,
    LifecycleTabRow,
    LoanMixItem,
    OfficerBranchData,
    SingleLoanCount,
    TopBorrower,
    WatchlistTrendPoint,
    WaterfallStep,
)
from fastapi.testclient import TestClient


def _officer_branch(
    tab_data: list[LifecycleTabRow] | None = None,
) -> OfficerBranchData:
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
        change_by_type_waterfall=[WaterfallStep(product="Auto", delta=50_000.0)],
        single_loan_customers_by_type=[SingleLoanCount(product="Auto", count=80)],
        combo_balance_rate=[
            ComboBalanceRate(
                product="Auto", balance=4_000_000.0, weighted_avg_rate=0.065
            )
        ],
        watchlist_trend=[
            WatchlistTrendPoint(month="2026-04", count=5, balance=250_000.0)
        ],
        tab_data=tab_data,
    )


def _simple_compose(
    as_of: date,
    db_url: str,
    branch_id: int | None = None,
    officer_id: str | None = None,
    tab: str | None = None,
) -> OfficerBranchData:
    return _officer_branch()


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
        _simple_compose,
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/dashboards/officer-branch")
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
        _simple_compose,
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/dashboards/officer-branch")
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
        tab: str | None = None,
    ) -> OfficerBranchData:
        nonlocal call_count
        call_count += 1
        return _officer_branch()

    monkeypatch.setattr("api.service.dashboard_query.compose_officer_branch", _compose)
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    client.get("/dashboards/officer-branch?as_of_date=2026-03-01")
    client.get("/dashboards/officer-branch?as_of_date=2026-03-01")
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
        tab: str | None = None,
    ) -> OfficerBranchData:
        received["branch_id"] = branch_id
        received["officer_id"] = officer_id
        return _officer_branch()

    monkeypatch.setattr("api.service.dashboard_query.compose_officer_branch", _compose)
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get(
        "/dashboards/officer-branch?as_of_date=2026-02-01&branch_id=3&officer_id=abc"
    )
    assert resp.status_code == 200
    assert received["branch_id"] == 3
    assert received["officer_id"] == "abc"


def test_tab_new_returns_tab_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab_row = LifecycleTabRow(
        period="2026-03", product_type="Auto", count=12, amount=480_000.0
    )

    def _compose_new(*_a: object, **_k: object) -> OfficerBranchData:
        return _officer_branch(tab_data=[tab_row])

    monkeypatch.setattr(
        "api.repo.loans.fetch_latest_loans_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_officer_branch",
        _compose_new,
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/dashboards/officer-branch?tab=new")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"]["tab_data"], list)
    assert body["data"]["tab_data"][0]["product_type"] == "Auto"


def test_tab_paid_off_returns_tab_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab_row = LifecycleTabRow(
        period="2026-03", product_type="Mortgage", count=3, amount=900_000.0
    )

    def _compose_paid(*_a: object, **_k: object) -> OfficerBranchData:
        return _officer_branch(tab_data=[tab_row])

    monkeypatch.setattr(
        "api.repo.loans.fetch_latest_loans_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_officer_branch",
        _compose_paid,
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/dashboards/officer-branch?tab=paid_off")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"]["tab_data"], list)
    assert body["data"]["tab_data"][0]["product_type"] == "Mortgage"


def test_no_tab_omits_tab_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.loans.fetch_latest_loans_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_officer_branch",
        _simple_compose,
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/dashboards/officer-branch")
    assert resp.status_code == 200
    assert resp.json()["data"]["tab_data"] is None


def test_watchlist_trend_always_present(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.repo.loans.fetch_latest_loans_month",
        lambda db_url: date(2026, 4, 1),
    )
    monkeypatch.setattr(
        "api.service.dashboard_query.compose_officer_branch",
        _simple_compose,
    )
    monkeypatch.setattr(
        "api.routes.dashboards.save_dashboard_audit", lambda *a, **k: None
    )

    resp = client.get("/dashboards/officer-branch")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"]["watchlist_trend"], list)
    assert len(body["data"]["watchlist_trend"]) >= 1
