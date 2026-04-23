"""Tests for HUG-31: FastAPI routes."""

import pytest
from api.main import app
from fastapi.testclient import TestClient
from nl_engine.engine import AnswerResponse, ClarificationResponse


def _answer() -> AnswerResponse:
    return AnswerResponse(
        sql="SELECT 1",
        explanation="test",
        tables_used=["fct_loan_originations"],
        assumptions=[],
        caveats=[],
        rows=[{"n": 1}],
        columns=["n"],
    )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.ctx = object()
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


def test_ask_returns_answer(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("api.routes.ask.engine_ask", lambda *_a, **_kw: _answer())
    monkeypatch.setattr("api.routes.ask.save_query", lambda *_a, **_kw: None)
    resp = client.post("/ask", json={"question": "How many loans?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sql"] == "SELECT 1"
    assert data["request_id"] != ""


def test_ask_returns_clarification(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.ask.engine_ask",
        lambda *_a, **_kw: ClarificationResponse(question="Which metric?"),
    )
    resp = client.post("/ask", json={"question": "What's the rate?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["clarification"] == "Which metric?"
    assert data["sql"] is None


def test_request_id_in_response_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("api.routes.ask.engine_ask", lambda *_a, **_kw: _answer())
    monkeypatch.setattr("api.routes.ask.save_query", lambda *_a, **_kw: None)
    resp = client.post("/ask", json={"question": "How many loans?"})
    assert "x-request-id" in resp.headers
    assert resp.headers["x-request-id"] != ""


def test_ask_saves_to_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def capture_save(
        question: str, result: object, request_id: str, db_url: str
    ) -> None:
        calls.append(question)

    monkeypatch.setattr("api.routes.ask.engine_ask", lambda *_a, **_kw: _answer())
    monkeypatch.setattr("api.routes.ask.save_query", capture_save)
    client.post("/ask", json={"question": "How many loans?"})
    assert calls == ["How many loans?"]
