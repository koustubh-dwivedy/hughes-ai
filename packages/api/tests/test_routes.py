"""Tests for the FastAPI routes (post-Surface-1, HUG-193)."""

import uuid
from datetime import UTC, datetime

import pytest
from api.main import app
from api.repo.trust import TrustStats
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.db_url = "postgresql://localhost/cubi"
        return c


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_ok(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# /history
# ---------------------------------------------------------------------------

_RECORD_ID = uuid.uuid4()
_NOW = datetime.now(tz=UTC)


def _history_row() -> dict[str, object]:
    return {
        "id": _RECORD_ID,
        "question": "How many loans?",
        "sql": "SELECT 1",
        "answer_json": {"explanation": "test", "rows": [], "columns": []},
        "assumptions": [],
        "caveats": [],
        "lineage_json": {"tables_used": ["fct_loan_originations"]},
        "token_usage": {},
        "created_at": _NOW,
    }


def test_get_history_returns_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.history.get_history",
        lambda limit, db_url, kind=None: [_history_row(), _history_row()],
    )
    resp = client.get("/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_history_detail_ok(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.history.get_history_by_id",
        lambda record_id, db_url: _history_row(),
    )
    resp = client.get(f"/history/{_RECORD_ID}")
    assert resp.status_code == 200
    assert resp.json()["question"] == "How many loans?"


def test_get_history_detail_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.history.get_history_by_id",
        lambda record_id, db_url: None,
    )
    resp = client.get(f"/history/{_RECORD_ID}")
    assert resp.status_code == 404


# /history/{id}/rerun was removed in HUG-193 — its only purpose was
# re-executing Surface 1 SQL. Tests deleted with the endpoint.


# ---------------------------------------------------------------------------
# /trust
# ---------------------------------------------------------------------------


def test_get_trust_returns_stats(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.trust.get_trust_stats",
        lambda db_url: TrustStats(
            origence_row_count=10,
            symitar_row_count=8,
            reconciliation_match_rate=0.9,
        ),
    )
    resp = client.get("/trust")
    assert resp.status_code == 200
    data = resp.json()
    assert data["origence_row_count"] == 10
    assert data["symitar_row_count"] == 8
    assert data["reconciliation_match_rate"] == 0.9
    # Static caveat survives Surface 1 retirement (HUG-193).
    assert any("Deposits are sourced" in c for c in data["known_caveats"])
