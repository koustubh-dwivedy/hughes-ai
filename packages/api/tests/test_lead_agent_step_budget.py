"""Verifies `stream_lead_turn` invokes the agent with the lead's cap
(LEAD_MAX_STEPS_PER_TURN = 20) and the lead's restricted toolset
(LEAD_AGENT_TOOLS, no direct data fetches).

These two guarantees are the difference between the chat and lead
paths. If either drifts, deep-research questions either hit the cap
prematurely (cap regression) or bypass the delegation contract by
calling mf_query directly (toolset regression).
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any
from uuid import uuid4

import pytest
from api.services import agent_runner
from api.services.lead_agent import stream_lead_turn
from nl_engine.agent.state import LEAD_MAX_STEPS_PER_TURN
from nl_engine.agent.tools import LEAD_AGENT_TOOLS


class _FakeLLM:
    """Stand-in LLM; never invoked because run_agent_isolated is patched."""


def test_stream_lead_turn_passes_lead_cap_and_lead_toolset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def _spy(*_args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        if False:
            yield  # pragma: no cover

    monkeypatch.setattr("api.services.lead_agent.run_agent_isolated", _spy)
    monkeypatch.setattr(
        "api.services.lead_agent.threads_repo.append_message",
        lambda **_kw: None,
    )

    async def _drive() -> None:
        async for _ in stream_lead_turn(
            thread_id=uuid4(),
            user_content="anything",
            db_url="postgresql://stub",
            llm=_FakeLLM(),  # type: ignore[arg-type]
            history=[],
            request_id="test-req",
        ):
            pass

    asyncio.run(_drive())

    assert captured["max_steps"] == LEAD_MAX_STEPS_PER_TURN
    assert captured["max_steps"] == 20
    assert captured["tools"] is LEAD_AGENT_TOOLS
    tool_names = {t.name for t in captured["tools"]}
    assert "mf_query" not in tool_names, (
        "lead path must not be given mf_query — regression on delegation contract"
    )
    assert "run_subagent" in tool_names
    assert "propose_plan" in tool_names


def test_stream_user_turn_still_passes_chat_cap() -> None:
    """Changing the lead's cap must NOT bleed into the chat path."""
    src = inspect.getsource(agent_runner.stream_user_turn)
    assert "MAX_STEPS_PER_TURN" in src
    assert "LEAD_MAX_STEPS_PER_TURN" not in src
