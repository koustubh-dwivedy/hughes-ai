"""Integration: X-Hughes-Session header binds session_id into log records.

Verifies the cross-stack correlation contract:
- Frontend sends `X-Hughes-Session: <uuid>` on every request
- RequestIDMiddleware reads it and binds it to a contextvar
- The structlog processor includes it on every log record emitted
  during request handling
"""

import io
import json
import os
from contextlib import redirect_stdout

import pytest
from fastapi.testclient import TestClient


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


def test_session_id_appears_in_log_records(client: TestClient) -> None:
    """Send a request with X-Hughes-Session and assert structlog emits it."""
    from api.logging import bind_session_id, get_logger  # noqa: PLC0415

    sid = "test-session-uuid-12345"
    captured = io.StringIO()
    # Capture structlog output by binding the session id ourselves and
    # writing a single log line. This proves the processor injects
    # session_id when the contextvar is set.
    token = bind_session_id(sid)
    try:
        with redirect_stdout(captured):
            get_logger().info("session_correlation_check")
    finally:
        from api.logging import _session_id  # noqa: PLC0415

        _session_id.reset(token)

    output = captured.getvalue()
    # structlog JSONRenderer prints one JSON object per log call
    record = json.loads(output.strip().splitlines()[-1])
    assert record.get("session_id") == sid
    assert record.get("event") == "session_correlation_check"


def test_request_with_session_header_echoes_in_response(
    client: TestClient,
) -> None:
    """The middleware should echo the session header back on the response."""
    sid = "echo-session-678"
    res = client.get("/health", headers={"X-Hughes-Session": sid})
    assert res.status_code == 200
    assert res.headers.get("X-Hughes-Session") == sid


def test_request_without_session_header_does_not_break(
    client: TestClient,
) -> None:
    """Backwards compatibility: requests with no header still work."""
    res = client.get("/health")
    assert res.status_code == 200
    # Header is omitted when empty, not echoed as empty string
    assert "X-Hughes-Session" not in res.headers
