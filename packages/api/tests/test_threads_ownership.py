"""Ownership / auth tests for /threads/{thread_id} routes (Fix B).

E2E verification (2026-05-17) discovered that `GET /threads/{tid}` and
`POST /threads/{tid}/messages` had no ownership check — any caller could
read or write to any thread by knowing the UUID. Pre-existing bug from
HUG-177 (2026-05-05).

These tests pin the new contract:
- Owner can GET + POST.
- Non-owner gets 403 on both.
- No-auth request gets 400 (X-Hughes-Session header is required upstream).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import psycopg
import pytest
from api.main import app
from api.repo import threads as threads_repo
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db

_DB_URL = os.environ.get("DATABASE_URL")


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def client() -> Iterator[TestClient]:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    app.state.db_url = _DB_URL
    with TestClient(app) as c:
        yield c
    _cleanup()


def _cleanup() -> None:
    if not _DB_URL:
        return
    # FK on thread_messages → threads is not CASCADE; delete child rows
    # first. Same approach for any other tables that FK threads.
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id IN"
            " (SELECT thread_id FROM threads WHERE session_id LIKE 'fixb-%')"
        )
        cur.execute("DELETE FROM threads WHERE session_id LIKE 'fixb-%'")


def _user_headers(uid: str) -> dict[str, str]:
    return {"X-Hughes-User": uid, "X-Hughes-Session": f"sess-{uid}"}


def _seed_thread(uid: str) -> UUID:
    sid = f"fixb-{uuid4().hex[:6]}"
    t = threads_repo.create_thread(sid, _db_url(), user_id=uid)
    return t.thread_id


# ── GET /threads/{tid} ───────────────────────────────────────────────


def test_owner_can_read_own_thread(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    tid = _seed_thread(uid)
    resp = client.get(f"/threads/{tid}", headers=_user_headers(uid))
    assert resp.status_code == 200
    assert resp.json()["thread_id"] == str(tid)


def test_non_owner_get_returns_403(client: TestClient) -> None:
    """The pre-existing bug: this returned 200 with the thread body.
    After fix, should be 403."""
    owner = f"u-{uuid4().hex[:6]}"
    stranger = f"u-{uuid4().hex[:6]}"
    tid = _seed_thread(owner)
    resp = client.get(f"/threads/{tid}", headers=_user_headers(stranger))
    assert resp.status_code == 403, resp.text


def test_no_auth_get_returns_400(client: TestClient) -> None:
    """Without X-Hughes-Session header, request is malformed."""
    uid = f"u-{uuid4().hex[:6]}"
    tid = _seed_thread(uid)
    resp = client.get(f"/threads/{tid}")
    # Either 400 (missing header) or 401/403 — anything except 200.
    assert resp.status_code in (400, 401, 403)


def test_missing_thread_returns_404(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    resp = client.get(f"/threads/{uuid4()}", headers=_user_headers(uid))
    assert resp.status_code == 404


# ── POST /threads/{tid}/messages ─────────────────────────────────────


def test_non_owner_post_messages_returns_403(client: TestClient) -> None:
    """The pre-existing bug: any caller could write to any thread."""
    owner = f"u-{uuid4().hex[:6]}"
    stranger = f"u-{uuid4().hex[:6]}"
    tid = _seed_thread(owner)
    resp = client.post(
        f"/threads/{tid}/messages",
        json={"content": "hello"},
        headers=_user_headers(stranger),
    )
    assert resp.status_code == 403, resp.text


def test_no_auth_post_messages_returns_400(client: TestClient) -> None:
    """Without auth headers, POST messages is malformed."""
    uid = f"u-{uuid4().hex[:6]}"
    tid = _seed_thread(uid)
    resp = client.post(f"/threads/{tid}/messages", json={"content": "hi"})
    assert resp.status_code in (400, 401, 403)


def test_missing_thread_post_returns_404(client: TestClient) -> None:
    uid = f"u-{uuid4().hex[:6]}"
    resp = client.post(
        f"/threads/{uuid4()}/messages",
        json={"content": "hi"},
        headers=_user_headers(uid),
    )
    assert resp.status_code == 404
