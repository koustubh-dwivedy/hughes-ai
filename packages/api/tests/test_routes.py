"""Tests for HUG-31 + HUG-32: FastAPI routes."""

import uuid
from datetime import UTC, datetime

import pytest
from api.main import app
from api.repo.trust import TrustStats
from fastapi.testclient import TestClient
from nl_engine.context_loader import AllContext, Column, Metric, Rule, Table
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


def _make_ctx() -> AllContext:
    col = Column(name="loan_id", type="UUID", description="", example="")
    table = Table(name="fct_loan_originations", description="", columns=[col])
    metric = Metric(
        name="approval_rate",
        label="Approval Rate",
        description="",
        formula_plain_english="",
        caveats="Exclude pending.",
        related_questions=[],
    )
    rule = Rule(id="r1", rule="Use funded_at", rationale="Standard")
    return AllContext(tables=[table], metrics=[metric], rules=[rule], examples=[])


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.ctx = _make_ctx()
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
        lambda limit, db_url: [_history_row(), _history_row()],
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


def test_rerun_ok(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.history.get_history_by_id",
        lambda record_id, db_url: _history_row(),
    )
    monkeypatch.setattr(
        "api.routes.history.execute_sql",
        lambda sql, db_url: ([{"n": 1}], ["n"]),
    )
    monkeypatch.setattr(
        "api.routes.history.save_query", lambda *_a, **_kw: None
    )
    resp = client.post(f"/history/{_RECORD_ID}/rerun")
    assert resp.status_code == 200
    assert resp.json()["sql"] == "SELECT 1"


def test_rerun_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.routes.history.get_history_by_id",
        lambda record_id, db_url: None,
    )
    resp = client.post(f"/history/{_RECORD_ID}/rerun")
    assert resp.status_code == 404


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
    assert "Exclude pending." in data["known_caveats"]
    assert any("Deposits are sourced" in c for c in data["known_caveats"])
