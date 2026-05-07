"""HTTP-level tests for the /threads surface.

Live Postgres (use the same DATABASE_URL the integration suite uses).
A fake LLM is injected via app.state.agent_llm so the SSE round-trip
runs end-to-end without hitting Cerebras.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from api.main import app
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_DB_URL = os.environ.get("DATABASE_URL")


class _FakeLLM(BaseChatModel):
    responses: list[AIMessage]
    call_count: int = 0

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return ChatResult(generations=[ChatGeneration(message=self.responses[idx])])

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(  # type: ignore[override]
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FakeLLM:
        return self


@pytest.fixture
def client() -> Any:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    app.state.db_url = _DB_URL
    app.state.agent_llm = _FakeLLM(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "final_answer",
                        "args": {"summary": "ok", "rows": [{"x": 1}]},
                        "id": "c1",
                    }
                ],
            )
        ]
    )
    with TestClient(app) as c:
        yield c
    app.state.agent_llm = None
    _cleanup()


def _cleanup() -> None:
    if not _DB_URL:
        return
    with psycopg.connect(_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id IN ("
            "SELECT thread_id FROM threads WHERE session_id LIKE 'pytest-%'"
            ")"
        )
        cur.execute("DELETE FROM threads WHERE session_id LIKE 'pytest-%'")


def test_create_thread_requires_session_header(client: Any) -> None:
    resp = client.post("/threads", json={"title": "test"})
    assert resp.status_code == 400


def test_create_and_get_thread(client: Any) -> None:
    sid = f"pytest-{uuid4()}"
    resp = client.post(
        "/threads", json={"title": "demo"}, headers={"X-Hughes-Session": sid}
    )
    assert resp.status_code == 200
    body = resp.json()
    thread_id = body["thread_id"]
    assert body["title"] == "demo"
    fetched = client.get(f"/threads/{thread_id}")
    assert fetched.status_code == 200
    assert fetched.json()["thread_id"] == thread_id
    assert fetched.json()["messages"] == []


def test_list_threads_returns_session_threads(client: Any) -> None:
    sid = f"pytest-{uuid4()}"
    for title in ("a", "b", "c"):
        client.post(
            "/threads", json={"title": title}, headers={"X-Hughes-Session": sid}
        )
    resp = client.get("/threads", headers={"X-Hughes-Session": sid})
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()["threads"]]
    assert set(titles) == {"a", "b", "c"}


def test_post_message_streams_final_event(client: Any) -> None:
    sid = f"pytest-{uuid4()}"
    created = client.post(
        "/threads", json={"title": None}, headers={"X-Hughes-Session": sid}
    )
    thread_id = created.json()["thread_id"]
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "How many metrics?"},
    ) as stream:
        events = list(_parse_sse(stream.iter_lines()))
    kinds = [e["event"] for e in events]
    assert "step" in kinds
    assert "final" in kinds
    final = next(e for e in events if e["event"] == "final")
    payload = json.loads(final["data"])
    assert payload["message"]["role"] == "tool"
    fetched = client.get(f"/threads/{thread_id}").json()
    roles = [m["role"] for m in fetched["messages"]]
    assert roles == ["user", "assistant", "tool"]


def _parse_sse(lines: Any) -> Any:
    event = None
    data: list[str] = []
    for raw in lines:
        line = raw.strip() if isinstance(raw, str) else raw.decode().strip()
        if not line:
            if event is not None:
                yield {"event": event, "data": "\n".join(data)}
            event = None
            data = []
            continue
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data.append(line.split(":", 1)[1].strip())
