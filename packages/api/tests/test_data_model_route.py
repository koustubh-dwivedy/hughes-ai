"""Route tests for /data-model endpoints (mocked repo + DB)."""

from __future__ import annotations

import pytest
from api.main import app
from fastapi.testclient import TestClient


def _manifest() -> dict:
    return {
        "nodes": {
            "model.hughes_ai.fct_loans_monthly": {
                "unique_id": "model.hughes_ai.fct_loans_monthly",
                "name": "fct_loans_monthly",
                "resource_type": "model",
                "fqn": ["hughes_ai", "marts", "fct_loans_monthly"],
                "description": "Monthly loan rollup.",
                "config": {"materialized": "table"},
                "depends_on": {"nodes": ["source.hughes_ai.raw.booked_loans"]},
                "columns": {
                    "as_of_month": {
                        "name": "as_of_month",
                        "data_type": "DATE",
                        "description": "Month start.",
                    },
                },
                "raw_code": "SELECT 1",
                "original_file_path": "models/marts/fct_loans_monthly.sql",
            },
        },
        "sources": {
            "source.hughes_ai.raw.booked_loans": {
                "unique_id": "source.hughes_ai.raw.booked_loans",
                "name": "booked_loans",
                "resource_type": "source",
                "fqn": ["hughes_ai", "staging", "raw", "booked_loans"],
                "description": "",
                "source_name": "raw",
                "original_file_path": "models/staging/sources.yml",
            },
        },
    }


def _dashboard_map() -> list[dict]:
    return [
        {
            "id": "dashboard.executive",
            "name": "Executive Summary",
            "route": "/dashboards/executive",
            "backed_by": ["fct_loans_monthly"],
        },
    ]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/cubi")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    monkeypatch.setattr("api.routes.data_model.repo_dm.load_manifest", _manifest)
    monkeypatch.setattr(
        "api.routes.data_model.repo_dm.load_dashboard_mapping", _dashboard_map
    )
    monkeypatch.setattr(
        "api.routes.data_model.repo_dm.load_run_results", lambda: {}
    )
    monkeypatch.setattr(
        "api.routes.data_model.repo_dm.count_nl_queries_per_table",
        lambda *_a, **_k: {"fct_loans_monthly": 3},
    )

    audit_calls: list[tuple] = []

    def capture_audit(endpoint: str, params: dict, audit_id, db_url: str) -> None:
        audit_calls.append((endpoint, dict(params), str(audit_id)))

    monkeypatch.setattr(
        "api.routes.data_model.save_dashboard_audit", capture_audit
    )

    with TestClient(app, raise_server_exceptions=True) as c:
        app.state.db_url = "postgresql://localhost/cubi"
        c.audit_calls = audit_calls  # type: ignore[attr-defined]
        return c


def test_graph_returns_nodes_and_edges(client: TestClient) -> None:
    resp = client.get("/data-model/graph")
    assert resp.status_code == 200
    body = resp.json()
    ids = {n["id"] for n in body["nodes"]}
    assert "source.hughes_ai.raw.booked_loans" in ids
    assert "model.hughes_ai.fct_loans_monthly" in ids
    assert "dashboard.executive" in ids
    assert any(
        e["source"] == "model.hughes_ai.fct_loans_monthly"
        and e["target"] == "dashboard.executive"
        for e in body["edges"]
    )
    assert "audit_id" in body


def test_graph_stamps_nl_counts(client: TestClient) -> None:
    resp = client.get("/data-model/graph")
    fct = next(
        n for n in resp.json()["nodes"] if n["name"] == "fct_loans_monthly"
    )
    assert fct["nl_query_count_30d"] == 3


def test_graph_writes_audit(client: TestClient) -> None:
    client.get("/data-model/graph")
    endpoints = [c[0] for c in client.audit_calls]  # type: ignore[attr-defined]
    assert "data-model-graph" in endpoints


def test_node_detail_returns_sql_and_columns(client: TestClient) -> None:
    resp = client.get("/data-model/nodes/model.hughes_ai.fct_loans_monthly")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sql"] == "SELECT 1"
    assert body["columns"][0]["name"] == "as_of_month"
    assert body["dashboards"][0]["route"] == "/dashboards/executive"


def test_node_detail_404_for_unknown(client: TestClient) -> None:
    resp = client.get("/data-model/nodes/model.hughes_ai.does_not_exist")
    assert resp.status_code == 404


def test_node_detail_writes_audit(client: TestClient) -> None:
    client.get("/data-model/nodes/model.hughes_ai.fct_loans_monthly")
    endpoints = [c[0] for c in client.audit_calls]  # type: ignore[attr-defined]
    assert "data-model-node" in endpoints
