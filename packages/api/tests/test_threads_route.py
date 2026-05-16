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

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

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

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> _FakeLLM:  # type: ignore[override]
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
    headers = {"X-Hughes-Session": sid}
    resp = client.post("/threads", json={"title": "demo"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    thread_id = body["thread_id"]
    assert body["title"] == "demo"
    fetched = client.get(f"/threads/{thread_id}", headers=headers)
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


def test_threads_filter_by_user_id_not_session_id(client: Any) -> None:
    """HUG-205: a thread created by user A must be visible to user A's
    later visits (different session_id) and invisible to user B."""
    user_a = f"user-a-{uuid4()}"
    user_b = f"user-b-{uuid4()}"
    visit_1 = f"visit-1-{uuid4()}"
    visit_2 = f"visit-2-{uuid4()}"
    # User A creates a thread during visit 1.
    client.post(
        "/threads",
        json={"title": "owned-by-a"},
        headers={"X-Hughes-User": user_a, "X-Hughes-Session": visit_1},
    )
    # User A returns later in a different visit (fresh session_id, same user_id).
    resp_a_revisit = client.get(
        "/threads",
        headers={"X-Hughes-User": user_a, "X-Hughes-Session": visit_2},
    )
    assert resp_a_revisit.status_code == 200
    titles_a = [t["title"] for t in resp_a_revisit.json()["threads"]]
    assert "owned-by-a" in titles_a
    # User B in a different visit (different user_id) does NOT see it.
    resp_b = client.get(
        "/threads",
        headers={"X-Hughes-User": user_b, "X-Hughes-Session": visit_2},
    )
    assert resp_b.status_code == 200
    titles_b = [t["title"] for t in resp_b.json()["threads"]]
    assert "owned-by-a" not in titles_b


def test_threads_falls_back_to_session_id_when_user_header_absent(client: Any) -> None:
    """Backwards-compat: a client that hasn't moved to X-Hughes-User
    should still see its threads via the X-Hughes-Session fallback."""
    sid = f"legacy-{uuid4()}"
    client.post(
        "/threads",
        json={"title": "legacy-thread"},
        headers={"X-Hughes-Session": sid},
    )
    resp = client.get("/threads", headers={"X-Hughes-Session": sid})
    titles = [t["title"] for t in resp.json()["threads"]]
    assert "legacy-thread" in titles


def test_post_message_streams_final_event(client: Any) -> None:
    sid = f"pytest-{uuid4()}"
    headers = {"X-Hughes-Session": sid}
    created = client.post("/threads", json={"title": None}, headers=headers)
    thread_id = created.json()["thread_id"]
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "How many metrics?"},
        headers=headers,
    ) as stream:
        events = list(_parse_sse(stream.iter_lines()))
    kinds = [e["event"] for e in events]
    assert "step" in kinds
    assert "final" in kinds
    final = next(e for e in events if e["event"] == "final")
    payload = json.loads(final["data"])
    assert payload["message"]["role"] == "tool"
    fetched = client.get(f"/threads/{thread_id}", headers=headers).json()
    roles = [m["role"] for m in fetched["messages"]]
    assert roles == ["user", "assistant", "tool"]


def test_post_message_stamps_thread_title_in_background(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First user message on a title=None thread triggers a
    background LLM call that stamps a sidebar title."""
    import time

    from api.routes import threads as routes_threads

    monkeypatch.setattr(
        routes_threads, "generate_title",
        lambda msg, _llm: f"Title for: {msg[:30]}",
    )
    sid = f"pytest-{uuid4()}"
    headers = {"X-Hughes-Session": sid}
    created = client.post("/threads", json={"title": None}, headers=headers)
    thread_id = created.json()["thread_id"]
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "what is the delinquency rate"},
        headers=headers,
    ) as stream:
        list(_parse_sse(stream.iter_lines()))

    # Background task runs concurrent with response cleanup. Poll the
    # DB briefly until the title appears (or give up after 2 seconds).
    title = None
    for _ in range(20):
        fetched = client.get(f"/threads/{thread_id}", headers=headers).json()
        title = fetched["title"]
        if title is not None:
            break
        time.sleep(0.1)
    assert title == "Title for: what is the delinquency rate"


def test_post_message_emits_title_sse_event(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wrapper yields a `title` SSE event after `final` so the frontend
    re-fetches without a fallback timer."""
    from api.routes import threads as routes_threads

    monkeypatch.setattr(
        routes_threads, "generate_title", lambda msg, _llm: f"SSE title: {msg[:24]}"
    )
    sid = f"pytest-{uuid4()}"
    headers = {"X-Hughes-Session": sid}
    created = client.post("/threads", json={"title": None}, headers=headers)
    thread_id = created.json()["thread_id"]
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "approval rate by branch"},
        headers=headers,
    ) as stream:
        events = list(_parse_sse(stream.iter_lines()))
    kinds = [e["event"] for e in events]
    assert "title" in kinds, f"no title event in stream; got {kinds}"
    payload = json.loads(next(e for e in events if e["event"] == "title")["data"])
    assert payload == {
        "thread_id": thread_id,
        "title": "SSE title: approval rate by branch",
    }
    assert kinds.index("title") > kinds.index("final")


def test_post_message_does_not_overwrite_existing_title(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a thread already has a title (manually-set or previously
    auto-generated), subsequent messages must not re-stamp it."""
    from api.routes import threads as routes_threads

    monkeypatch.setattr(
        routes_threads, "generate_title", lambda *_args, **_kw: "Should not appear"
    )

    sid = f"pytest-{uuid4()}"
    headers = {"X-Hughes-Session": sid}
    created = client.post("/threads", json={"title": "Manually named"}, headers=headers)
    thread_id = created.json()["thread_id"]
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "first message"},
        headers=headers,
    ) as stream:
        list(_parse_sse(stream.iter_lines()))
    fetched = client.get(f"/threads/{thread_id}", headers=headers).json()
    assert fetched["title"] == "Manually named"


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
