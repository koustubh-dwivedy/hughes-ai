"""Robustness tests for the agent step (HUG-190 Phase C).

Covers:
- Token-overflow guard truncates oldest non-system messages
- LLM exception inside `_make_agent_step` returns a graceful AIMessage
  instead of crashing the graph (so the SSE stream can complete)
- The truncation guard preserves the SystemMessage and the recent tail
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from nl_engine.agent import graph as graph_mod
from nl_engine.agent import history as history_mod
from nl_engine.agent.state import AgentState


class _StubLLM(BaseChatModel):
    raise_exc: BaseException | None = None
    response_content: str = "ok"
    seen_messages: list[list[BaseMessage]] = []

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Record what the agent passed in so the test can inspect truncation.
        type(self).seen_messages.append(list(messages))
        if self.raise_exc is not None:
            raise self.raise_exc
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.response_content))],
        )

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(self, tools: Any, **kwargs: Any) -> _StubLLM:  # type: ignore[override]
        return self


def _reset_stub() -> None:
    _StubLLM.seen_messages = []


def test_estimate_tokens_under_threshold_returns_messages_unchanged() -> None:
    msgs: list[BaseMessage] = [
        SystemMessage(content="sys"),
        HumanMessage(content="hi"),
    ]
    result = history_mod.truncate_history(msgs)
    assert result == msgs


def test_truncate_history_drops_oldest_non_system_when_over_budget() -> None:
    chunk_size = history_mod._TOKEN_BUDGET * history_mod._CHARS_PER_TOKEN_HEURISTIC
    big_chunk = "x" * chunk_size
    # Each non-system message is ~budget-sized; together they exceed budget.
    msgs: list[BaseMessage] = [
        SystemMessage(content="SYSTEM_PROMPT"),
        HumanMessage(content=big_chunk),  # oldest — should be dropped
        AIMessage(content=big_chunk),     # also dropped
        HumanMessage(content="recent"),   # kept
    ]
    result = history_mod.truncate_history(msgs)
    # System message preserved
    assert isinstance(result[0], SystemMessage)
    assert result[0].content == "SYSTEM_PROMPT"
    # Recent tail preserved
    assert result[-1].content == "recent"
    # Some messages dropped
    assert len(result) < len(msgs)


def test_agent_step_catches_llm_exception_returns_graceful_aimessage() -> None:
    _reset_stub()
    llm = _StubLLM(raise_exc=RuntimeError("synthesized LLM error"))
    step = graph_mod._make_agent_step(llm, [])
    state = AgentState(
        messages=[HumanMessage(content="What's our LTD ratio?")],
        thread_id="t-1",
    )
    out = step(state)
    assert "messages" in out
    assert len(out["messages"]) == 1
    msg = out["messages"][0]
    assert isinstance(msg, AIMessage)
    assert "error" in msg.content.lower()
    # Step counter still increments so the loop's step-cap budgets the
    # failed call (graceful, not free).
    assert out["step_count"] == 1


def test_agent_step_normal_path_returns_llm_response() -> None:
    _reset_stub()
    llm = _StubLLM(response_content="from-llm")
    step = graph_mod._make_agent_step(llm, [])
    state = AgentState(
        messages=[HumanMessage(content="hi")],
        thread_id="t-2",
    )
    out = step(state)
    assert isinstance(out["messages"][0], AIMessage)
    assert out["messages"][0].content == "from-llm"
    assert out["step_count"] == 1


def test_agent_step_retries_transient_llm_error_then_succeeds(
    monkeypatch: Any,
) -> None:
    """HUG-190 Phase C-bis: a transient LLM error (e.g., Ollama 500)
    is retried up to twice before falling back to the graceful AIMessage.
    Same provider — NOT a fallback to a different provider.
    """
    _reset_stub()
    calls = {"n": 0}

    class _FlakyLLM(BaseChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("Internal Server Error (500)")
            return ChatResult(
                generations=[
                    ChatGeneration(message=AIMessage(content="recovered"))
                ],
            )

        @property
        def _llm_type(self) -> str:
            return "flaky-stub"

        def bind_tools(self, tools, **kwargs):
            return self

    monkeypatch.setattr(graph_mod.time, "sleep", lambda _s: None)
    step = graph_mod._make_agent_step(_FlakyLLM(), [])
    state = AgentState(messages=[HumanMessage(content="ping")], thread_id="t-1")
    out = step(state)
    assert calls["n"] == 2  # 1 failed + 1 retry succeeded
    assert isinstance(out["messages"][0], AIMessage)
    assert out["messages"][0].content == "recovered"


def test_agent_step_does_not_retry_non_transient_error() -> None:
    """Auth errors, malformed-prompt errors, etc. do NOT retry — they
    surface immediately as graceful AIMessage. Retrying wouldn't help."""
    _reset_stub()
    llm = _StubLLM(raise_exc=ValueError("invalid API key (auth failed)"))
    step = graph_mod._make_agent_step(llm, [])
    state = AgentState(messages=[HumanMessage(content="ping")], thread_id="t-1")
    out = step(state)
    assert isinstance(out["messages"][0], AIMessage)
    assert "error" in out["messages"][0].content.lower()


def test_agent_step_exhausts_retries_then_falls_back(monkeypatch: Any) -> None:
    """If retries are exhausted on persistent transient errors, fall back
    to the graceful AIMessage. Don't retry forever."""
    _reset_stub()
    monkeypatch.setattr(graph_mod.time, "sleep", lambda _s: None)
    llm = _StubLLM(raise_exc=RuntimeError("503 Service Unavailable"))
    step = graph_mod._make_agent_step(llm, [])
    state = AgentState(messages=[HumanMessage(content="ping")], thread_id="t-1")
    out = step(state)
    assert isinstance(out["messages"][0], AIMessage)
    assert "error" in out["messages"][0].content.lower()


def test_wall_clock_timeout_breaks_a_hung_invoke(monkeypatch: Any) -> None:
    """HUG-190 Phase C-bis²: when bound.invoke() hangs (e.g., underlying
    HTTP read never returns), the wall-clock wrapper forces a TimeoutError
    that the transient-retry loop catches."""
    import threading
    import time as real_time

    # `monkeypatch.setattr(graph_mod.time, "sleep", ...)` mutates the
    # global `time` module, so we can't use `time.sleep` in the hang —
    # use threading.Event().wait() which doesn't go through time.sleep.
    never_set = threading.Event()

    class _HangingLLM(BaseChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            never_set.wait(timeout=30)  # blocks the worker thread cleanly
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="never"))]
            )

        @property
        def _llm_type(self) -> str:
            return "hanging-stub"

        def bind_tools(self, tools, **kwargs):
            return self

    monkeypatch.setenv("AGENT_STEP_TIMEOUT_S", "0.3")
    monkeypatch.setattr(graph_mod.time, "sleep", lambda _s: None)

    step = graph_mod._make_agent_step(_HangingLLM(), [])
    state = AgentState(messages=[HumanMessage(content="ping")], thread_id="t-h")
    t0 = real_time.monotonic()
    out = step(state)
    elapsed = real_time.monotonic() - t0
    # Three attempts × 0.3s + ThreadPoolExecutor shutdown wait per attempt.
    # We expect well under the 30s `never_set.wait` budget. The wrapper's
    # `with ThreadPoolExecutor(...) as ex:` blocks on shutdown until each
    # worker thread finishes, but after `result(timeout=0.3)` raises, the
    # next iteration's executor exit waits for the prior thread —
    # bounded by `never_set.wait`'s 30s. So total < ~30s overall.
    # With the daemon-thread implementation, the wrapper returns
    # immediately on timeout (doesn't wait for the hung thread). 3 retries
    # × 0.3s ≈ 1s. We assert generously to avoid CI flakiness.
    assert elapsed < 5.0, (
        f"wall-clock guard didn't break hang; elapsed={elapsed:.1f}s"
    )
    # The graceful fallback message should appear (retries exhausted).
    assert isinstance(out["messages"][0], AIMessage)
    assert "error" in out["messages"][0].content.lower()


def test_invoke_with_wall_timeout_passes_through_normal_response() -> None:
    """When invoke() returns within the budget, the wrapper just returns
    the value unchanged."""

    class _Quick:
        def invoke(self, msgs):
            return AIMessage(content="quick")

    from nl_engine.agent.llm_invoke import invoke_with_wall_timeout
    out = invoke_with_wall_timeout(_Quick(), [], timeout_s=5.0)
    assert isinstance(out, AIMessage)
    assert out.content == "quick"


def test_is_transient_llm_error_detects_5xx_and_timeouts() -> None:
    assert graph_mod.is_transient_llm_error(RuntimeError("HTTP 500 Internal"))
    assert graph_mod.is_transient_llm_error(RuntimeError("503 Service Unavailable"))
    assert graph_mod.is_transient_llm_error(RuntimeError("request timed out"))
    assert graph_mod.is_transient_llm_error(RuntimeError("connection reset by peer"))
    # Non-transient errors don't trigger retry:
    assert not graph_mod.is_transient_llm_error(RuntimeError("invalid API key"))
    assert not graph_mod.is_transient_llm_error(RuntimeError("malformed prompt"))


def test_agent_step_prepends_system_prompt_and_truncates_in_one_pass() -> None:
    _reset_stub()
    llm = _StubLLM(response_content="ok")
    step = graph_mod._make_agent_step(llm, [])
    chunk_size = history_mod._TOKEN_BUDGET * history_mod._CHARS_PER_TOKEN_HEURISTIC
    big_chunk = "y" * chunk_size
    state = AgentState(
        messages=[
            HumanMessage(content=big_chunk),
            AIMessage(content=big_chunk),
            HumanMessage(content="recent"),
        ],
        thread_id="t-3",
    )
    step(state)
    seen = _StubLLM.seen_messages[-1]
    # First message must be the SystemMessage (prepended by _ensure_system_prompt)
    assert isinstance(seen[0], SystemMessage)
    # Tail must be the recent user message — the oldest two were truncated
    assert seen[-1].content == "recent"
