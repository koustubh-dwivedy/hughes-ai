"""HUG-200: agent telemetry — request_id propagation, structlog events,
Prometheus counters fire when expected."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from nl_engine.agent import graph as graph_mod
from nl_engine.agent.state import AgentState


class _FinalAnswerLLM(BaseChatModel):
    """Minimal LLM that emits a single final_answer tool call."""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {"summary": "ok"},
                    "id": "call_1",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(self, tools: Any, **kwargs: Any) -> _FinalAnswerLLM:  # type: ignore[override]
        return self


def test_request_id_threads_into_agent_state_request_id_field() -> None:
    """The request_id passed via _build_initial_state lands on AgentState."""
    from api.services.agent_runner import _build_initial_state

    rid = "req-123"
    state = _build_initial_state(uuid4(), "hello", history=[], request_id=rid)
    assert isinstance(state, AgentState)
    assert state.request_id == rid


def test_step_cap_increments_prometheus_counter() -> None:
    """Hitting the step cap increments hughes_agent_step_cap_hits_total."""
    from nl_engine.agent.metrics import agent_step_cap_hits_total

    before = agent_step_cap_hits_total._value.get()  # type: ignore[attr-defined]
    state = AgentState(
        messages=[], thread_id=str(uuid4()), step_count=10, request_id="rid-1"
    )
    out = graph_mod._step_cap_node(state)
    assert "messages" in out
    after = agent_step_cap_hits_total._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_tool_call_increments_per_tool_counter() -> None:
    """Each invocation of a tool increments hughes_agent_tool_calls_total."""
    from nl_engine.agent.metrics import agent_tool_calls_total

    tools_node = graph_mod._make_tools_node([])
    before = agent_tool_calls_total.labels(tool="final_answer")._value.get()  # type: ignore[attr-defined]
    last_ai = AIMessage(
        content="",
        tool_calls=[
            {"name": "final_answer", "args": {"summary": "x"}, "id": "c"}
        ],
    )
    state = AgentState(
        messages=[last_ai], thread_id=str(uuid4()), request_id="rid-x"
    )
    out = tools_node(state)
    assert isinstance(out["messages"][0], ToolMessage)
    after = agent_tool_calls_total.labels(tool="final_answer")._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_retry_reason_buckets_correctly() -> None:
    assert graph_mod._retry_reason(TimeoutError("timed out")) == "timeout"
    assert graph_mod._retry_reason(RuntimeError("503 Service Unavailable")) == "5xx"
    assert graph_mod._retry_reason(ValueError("nope")) == "other"


@pytest.mark.parametrize("rid", ["rid-A", ""])
def test_build_initial_state_handles_missing_request_id(rid: str) -> None:
    from api.services.agent_runner import _build_initial_state

    s = _build_initial_state(uuid4(), "q", history=[], request_id=rid)
    assert s.request_id == rid
