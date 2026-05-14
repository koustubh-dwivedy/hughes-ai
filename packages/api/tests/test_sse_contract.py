"""SSE event-contract gate (HUG-231).

Pins the ordered list of SSE `event:` field values emitted for each
public surface so renames / re-orderings during HUG-209+ work surface
as a CI failure with a clear diff, not a silent frontend regression.

Today's surfaces:
  - chat / research-shallow: chat agent driven via `route_turn` with a
    planner stub returning `route="shallow"`.

Future surfaces (added per phase as L2/E1/M3 etc land):
  - research-deep: planner returns `route="deep"` + plan; coordinator
    persists plan + emits `research.plan.drafted`; etc.

Goldens are short text files in `packages/api/tests/golden/`. To
refresh, run `make update-sse-goldens` (or set `UPDATE_SSE_GOLDENS=1`
in the env).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from api.main import app
from api.services.research_agent import coordinator
from api.services.research_agent.planner import PlanDraft
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

pytestmark = pytest.mark.db  # exercises threads route end-to-end (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")
_GOLDEN_DIR = Path(__file__).parent / "golden"
_UPDATE = os.environ.get("UPDATE_SSE_GOLDENS") == "1"


class _FinalAnswerLLM(BaseChatModel):
    """Returns one final_answer tool call every invoke. Deterministic."""

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content="",
            tool_calls=[{
                "name": "final_answer",
                "args": {"summary": "ok", "rows": [{"x": 1}]},
                "id": "c1",
            }],
        ))])

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FinalAnswerLLM:
        return self


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    app.state.db_url = _DB_URL
    app.state.agent_llm = _FinalAnswerLLM()

    # Bypass the live planner LLM call — return a deterministic shallow
    # verdict so the captured trace is the clean shallow path, not the
    # planner-error fallback path (which differs by one extra `error`
    # frame, would muddy the golden).
    def _stub_planner(_q: str, _h: Any, _l: Any) -> PlanDraft:
        return PlanDraft(
            route="shallow", reason="stub-shallow",
            plan=None, research_question_summary="stub",
        )
    monkeypatch.setattr(coordinator, "draft_plan", _stub_planner)

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
            "SELECT thread_id FROM threads WHERE session_id LIKE 'sse-contract-%'"
            ")"
        )
        cur.execute(
            "DELETE FROM threads WHERE session_id LIKE 'sse-contract-%'"
        )


def _parse_sse_event_types(lines: Iterator[bytes | str]) -> list[str]:
    """Pull only the `event:` field values, in order. Discard `data:`."""
    types: list[str] = []
    for raw in lines:
        line = raw.strip() if isinstance(raw, str) else raw.decode().strip()
        if line.startswith("event:"):
            types.append(line.split(":", 1)[1].strip())
    return types


def _capture_chat_turn(client: TestClient) -> list[str]:
    """Drive one chat turn end-to-end; return the ordered event types."""
    sid = f"sse-contract-{uuid4().hex[:8]}"
    created = client.post(
        "/threads",
        json={"title": "golden-trace"},
        headers={"X-Hughes-Session": sid},
    )
    thread_id = created.json()["thread_id"]
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "What is our deposit balance?"},
    ) as stream:
        return _parse_sse_event_types(stream.iter_lines())


def _assert_matches_golden(captured: list[str], name: str) -> None:
    golden_path = _GOLDEN_DIR / f"{name}.txt"
    if _UPDATE:
        _GOLDEN_DIR.mkdir(exist_ok=True)
        golden_path.write_text("\n".join(captured) + "\n")
        # When --update mode is on we just write + return; the test
        # body's caller prints the result via pytest -v output.
        return
    if not golden_path.exists():
        pytest.fail(
            f"golden missing: {golden_path.name}. Run "
            "`UPDATE_SSE_GOLDENS=1 pytest packages/api/tests/test_sse_contract.py` "
            "to seed it, then commit."
        )
    expected = [
        ln for ln in golden_path.read_text().splitlines() if ln.strip()
    ]
    if captured != expected:
        diff = "\n".join(
            f"  - {e}\n  + {c}" for e, c in zip(expected, captured, strict=False)
        )
        pytest.fail(
            f"SSE event sequence drifted from golden {golden_path.name}.\n"
            f"expected → captured:\n{diff}\n"
            f"expected length {len(expected)}, captured {len(captured)}.\n\n"
            "If the change is intentional, run "
            "`UPDATE_SSE_GOLDENS=1 pytest packages/api/tests/test_sse_contract.py` "
            "and commit the updated golden."
        )


def test_chat_turn_event_sequence(client: TestClient) -> None:
    """Today's chat surface = shallow research path."""
    captured = _capture_chat_turn(client)
    _assert_matches_golden(captured, "chat_turn")


def test_research_deep_turn_event_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HUG-209: deep turn emits exactly `research.plan.drafted`. Future
    L2/L4/E1/etc additions extend this golden as they land."""
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    app.state.db_url = _DB_URL
    app.state.agent_llm = _FinalAnswerLLM()

    def _stub_deep(_q: str, _h: Any, _l: Any) -> PlanDraft:
        return PlanDraft(
            route="deep", reason="stub-deep",
            plan=[
                {"ordinal": 1, "description": "x", "dependencies": []},
                {"ordinal": 2, "description": "y", "dependencies": [1]},
            ],
            research_question_summary="stub-deep",
        )
    monkeypatch.setattr(coordinator, "draft_plan", _stub_deep)

    with TestClient(app) as c:
        sid = f"sse-contract-{uuid4().hex[:8]}"
        created = c.post(
            "/threads", json={"title": "deep-golden"},
            headers={"X-Hughes-Session": sid},
        )
        thread_id = created.json()["thread_id"]
        with c.stream(
            "POST",
            f"/threads/{thread_id}/messages",
            json={"content": "decompose this question deeply"},
        ) as stream:
            captured = _parse_sse_event_types(stream.iter_lines())
    app.state.agent_llm = None
    _cleanup()
    _assert_matches_golden(captured, "research_deep_turn")


def test_chat_turn_final_event_payload_is_json(client: TestClient) -> None:
    """Spot-check: the `final` event's data is parseable JSON with a
    `message.role` field. Pins the data-shape contract alongside the
    event-type sequence — same surface, different invariant."""
    sid = f"sse-contract-{uuid4().hex[:8]}"
    created = client.post(
        "/threads",
        json={"title": "shape-test"},
        headers={"X-Hughes-Session": sid},
    )
    thread_id = created.json()["thread_id"]
    finals: list[dict[str, Any]] = []
    with client.stream(
        "POST",
        f"/threads/{thread_id}/messages",
        json={"content": "ping"},
    ) as stream:
        event = None
        data: list[str] = []
        for raw in stream.iter_lines():
            line = raw.strip() if isinstance(raw, str) else raw.decode().strip()
            if not line:
                if event == "final":
                    finals.append(json.loads("\n".join(data)))
                event = None
                data = []
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data.append(line.split(":", 1)[1].strip())
    assert finals, "no final event captured"
    assert finals[0]["message"]["role"] == "tool"
