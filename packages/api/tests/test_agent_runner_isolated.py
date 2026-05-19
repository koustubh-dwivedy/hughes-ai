"""Tests for `run_agent_isolated` — the F6 reuse primitive (HUG-206).

Pins the contract that both the chat shim (`stream_user_turn`) and
the deep-research worker (HUG-217, S1) will rely on:

  - With chat-shaped defaults (`chat_process_message`, full
    step cap), the primitive reproduces today's `stream_user_turn`
    event sequence.

  - With worker-shaped overrides (empty history, stub process_message,
    tighter cap), the primitive emits no thread_messages writes and
    forwards every AI/Tool message to the caller's callback.

  - `max_steps` flows into AgentState and is respected by the graph
    (`state.max_steps` now drives `_route`'s cap check).

Live Postgres; mirrors the fixture / fake-LLM pattern of
`test_research_coordinator.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from api.repo import threads as threads_repo
from api.services.agent_runner import run_agent_isolated, stream_user_turn
from api.services.agent_runner_chat import chat_process_message
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)

_DB_URL = os.environ.get("DATABASE_URL")


class _FinalAnswerLLM(BaseChatModel):
    """Stub that always responds with one `final_answer` tool call —
    drives the agent end-to-end in a single step."""

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
        msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {"summary": "ok", "rows": [{"x": 1}]},
                    "id": "c1",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(  # type: ignore[override]
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _FinalAnswerLLM:
        return self


class _NoTerminalLLM(BaseChatModel):
    """Stub that loops on a non-terminal tool — drives the agent
    until the step cap fires."""

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
        msg = AIMessage(
            content="",
            tool_calls=[{"name": "list_metrics", "args": {}, "id": "c-loop"}],
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(  # type: ignore[override]
        self, tools: Sequence[Any], **kwargs: Any
    ) -> _NoTerminalLLM:
        return self


def _db_url() -> str:
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    return _DB_URL  # type: ignore[return-value]


@pytest.fixture
def thread_id() -> UUID:
    db_url = _db_url()
    sid = f"pytest-runner-isolated-{uuid4().hex[:8]}"
    thread = threads_repo.create_thread(sid, db_url)
    yield thread.thread_id
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        cur.execute(
            "DELETE FROM threads WHERE thread_id = %s",
            (str(thread.thread_id),),
        )
        conn.commit()


async def _drain(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for ev in stream:
        out.append(ev)
    return out


def _count_thread_messages(thread_id: UUID) -> int:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM thread_messages WHERE thread_id = %s",
            (str(thread_id),),
        )
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


def test_chat_shaped_invocation_matches_stream_user_turn(
    thread_id: UUID,
) -> None:
    """Golden trace: calling `run_agent_isolated` with chat-shaped
    defaults produces the same event-type sequence as today's
    `stream_user_turn`. The chat shim itself layers a user-message
    persist on top; comparing event TYPES (not payloads) is the
    right granularity."""
    db_url = _db_url()
    llm = _FinalAnswerLLM()
    # Direct primitive call — no thread_messages write by the
    # primitive itself, but `chat_process_message` will persist
    # the assistant/tool rows.
    via_primitive = asyncio.run(
        _drain(
            run_agent_isolated(
                thread_id=thread_id,
                user_input="hi via primitive",
                history=[],
                db_url=db_url,
                llm=llm,
                process_message=chat_process_message,
                max_steps=10,
                request_id="rid-primitive",
            )
        )
    )
    # Clean up DB so the comparison call starts from the same state.
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM thread_messages WHERE thread_id = %s",
            (str(thread_id),),
        )
        conn.commit()
    via_shim = asyncio.run(
        _drain(
            stream_user_turn(
                thread_id=thread_id,
                user_content="hi via shim",
                db_url=db_url,
                llm=llm,
                history=[],
                request_id="rid-shim",
            )
        )
    )
    assert [e["event"] for e in via_primitive] == [
        e["event"] for e in via_shim
    ]
    assert "final" in {e["event"] for e in via_primitive}


def test_worker_shaped_invocation_writes_no_thread_messages(
    thread_id: UUID,
) -> None:
    """Worker scenario: empty history, stub process_message, no chat
    persistence callback. The primitive must NOT write any rows to
    thread_messages — that's what isolates workers from the chat
    surface."""
    db_url = _db_url()
    before = _count_thread_messages(thread_id)
    captured: list[Any] = []

    def stub_process_message(
        msg: Any,
        _step_idx: int,
        _thread_id: UUID,
        _db_url: str,
        _trace: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        captured.append(msg)
        return [{"event": "stub", "data": "ok"}]

    asyncio.run(
        _drain(
            run_agent_isolated(
                thread_id=thread_id,
                user_input="worker step description",
                history=[],
                db_url=db_url,
                llm=_FinalAnswerLLM(),
                process_message=stub_process_message,
                max_steps=5,
                request_id="rid-worker",
            )
        )
    )
    after = _count_thread_messages(thread_id)
    assert after == before, (
        f"worker path must not write thread_messages — wrote {after - before}"
    )
    # Stub captured both the AIMessage (with tool call) and the
    # synthesised ToolMessage from final_answer.
    assert len(captured) >= 1


def test_max_steps_caps_the_graph(thread_id: UUID) -> None:
    """`max_steps` plumbs through AgentState into `_route`'s cap
    comparison. Driving a non-terminal LLM with `max_steps=2`
    terminates via the step-cap node, not by running indefinitely.

    HUG-265 + HUG-269: when step-cap fires, `chat_process_message`
    synthesizes an `event: final` from the plaintext apology AIMessage
    so the SPA unlocks (instead of stranding the user on a stuck
    ThinkingBubble). The synthesized final's `message.content` carries
    the step-cap apology, NOT a real final_answer payload.
    """
    db_url = _db_url()
    events = asyncio.run(
        _drain(
            run_agent_isolated(
                thread_id=thread_id,
                user_input="loop forever, please",
                history=[],
                db_url=db_url,
                llm=_NoTerminalLLM(),
                process_message=chat_process_message,
                max_steps=2,
                request_id="rid-cap",
            )
        )
    )
    event_names = {e["event"] for e in events}
    assert "final" in event_names
    finals = [e for e in events if e["event"] == "final"]
    assert len(finals) == 1
    data = json.loads(finals[0]["data"])
    content = (data.get("message") or {}).get("content") or ""
    assert "couldn't reach an answer" in content


def test_initial_state_extras_lands_in_slots(thread_id: UUID) -> None:
    """`initial_state_extras` is the worker-friendly carrier for
    fields the graph needs to see (e.g. `step_id`). It must reach
    `AgentState.slots` so downstream tool nodes can read it."""
    from api.services.agent_runner import _build_initial_state

    state = _build_initial_state(
        thread_id=thread_id,
        user_input="hi",
        history=[],
        max_steps=5,
        request_id="rid",
        extras={"step_id": "abc-123", "subagent_id": "worker-7"},
    )
    assert state.slots == {"step_id": "abc-123", "subagent_id": "worker-7"}
    assert state.max_steps == 5
