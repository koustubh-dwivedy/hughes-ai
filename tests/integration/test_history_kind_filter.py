"""Integration test: GET /history?kind=ask filters out dashboard audit rows.

Seeds 10 'ask' + 10 'dashboard_audit' rows into query_history, then asserts
the FastAPI route returns exactly the 10 ask rows when kind=ask is passed.
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)


@pytest.fixture
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest.fixture
def client(db_url: str) -> TestClient:
    from api.main import app  # noqa: PLC0415

    app.state.db_url = db_url
    return TestClient(app)


@pytest.fixture
def seeded_history(db_url: str) -> Iterator[list[uuid.UUID]]:
    """Insert 10 ask + 10 dashboard_audit rows; clean up after the test."""
    ids: list[uuid.UUID] = []
    with psycopg.connect(db_url, autocommit=True) as conn:
        for i in range(10):
            ask_id = uuid.uuid4()
            ids.append(ask_id)
            conn.execute(
                "INSERT INTO query_history "
                "(id, question, sql, kind) VALUES (%s, %s, %s, %s)",
                (ask_id, f"ask question {i}", "SELECT 1", "ask"),
            )
            audit_id = uuid.uuid4()
            ids.append(audit_id)
            conn.execute(
                "INSERT INTO query_history "
                "(id, question, sql, kind) VALUES (%s, %s, %s, %s)",
                (
                    audit_id,
                    f"dashboard:foo:{i}",
                    "",
                    "dashboard_audit",
                ),
            )
    yield ids
    # Disable the append-only trigger temporarily for test cleanup, then
    # delete only the rows we inserted by id.
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute(
            "ALTER TABLE query_history "
            "DISABLE TRIGGER query_history_append_only"
        )
        try:
            conn.execute(
                "DELETE FROM query_history WHERE id = ANY(%s)",
                (ids,),
            )
        finally:
            conn.execute(
                "ALTER TABLE query_history "
                "ENABLE TRIGGER query_history_append_only"
            )


def test_history_kind_ask_returns_only_ask_rows(
    client: TestClient, seeded_history: list[uuid.UUID]
) -> None:
    res = client.get("/history?kind=ask&limit=50")
    assert res.status_code == 200
    rows = res.json()
    ask_ids = {str(seeded_history[i]) for i in range(0, 20, 2)}
    returned_ids = {row["id"] for row in rows}
    # Every ask row we seeded should be present
    assert ask_ids.issubset(returned_ids)
    # No dashboard_audit row should appear
    audit_ids = {str(seeded_history[i]) for i in range(1, 20, 2)}
    assert returned_ids.isdisjoint(audit_ids)
    # Every returned row must report kind == 'ask'
    for row in rows:
        assert row.get("kind") == "ask"


def test_history_kind_dashboard_audit_returns_only_audit_rows(
    client: TestClient, seeded_history: list[uuid.UUID]
) -> None:
    res = client.get("/history?kind=dashboard_audit&limit=50")
    assert res.status_code == 200
    rows = res.json()
    audit_ids = {str(seeded_history[i]) for i in range(1, 20, 2)}
    returned_ids = {row["id"] for row in rows}
    assert audit_ids.issubset(returned_ids)
    for row in rows:
        assert row.get("kind") == "dashboard_audit"


def test_history_invalid_kind_returns_400(client: TestClient) -> None:
    res = client.get("/history?kind=garbage")
    assert res.status_code == 400
