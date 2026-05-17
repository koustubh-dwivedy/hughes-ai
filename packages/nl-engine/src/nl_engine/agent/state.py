"""Typed conversational state shared across the LangGraph nodes.

Pydantic-typed so the contract between the orchestrator, the tool nodes,
and the persistence adapter is mechanical: every field is reachable from
a typed read at every layer. The `messages` list is the single
LangChain-native channel; everything else is bookkeeping the agent
needs to enforce its own invariants (step cap, turn boundaries).
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Hard cap on LLM calls per user turn — enforces liveness so a tool-call
# loop can never burn through the Cerebras rate-limit budget. Surfaces a
# graceful apology when reached (see graph.py:_step_cap_node).
#
# HUG-206 (F6) made this a per-turn parameter on AgentState. The module
# constant remains as the default so every existing call site (the chat
# `stream_user_turn`, the eval harness) keeps the original cap; the new
# `run_agent_isolated` primitive lets the worker path opt into a tighter
# cap (5) without disturbing the chat agent.
MAX_STEPS_PER_TURN = 10
# The autonomous lead path orchestrates rather than fetches: it pays one
# LLM call per propose_plan, per run_subagent dispatch, per memory write,
# and per final_answer. A typical deep question needs ~6-12 calls plus
# headroom for one replan. 20 holds meaning as a runaway guard; >25 would
# effectively be no ceiling.
LEAD_MAX_STEPS_PER_TURN = 20


class AgentState(BaseModel):
    """The full state object the LangGraph instance threads through nodes.

    `messages` is reduced by langgraph's add_messages so each node can
    return new messages without manually copying the prior list.
    """

    model_config = {"arbitrary_types_allowed": True}

    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    thread_id: str
    step_count: int = 0
    # Per-turn cap (HUG-206). Defaults to MAX_STEPS_PER_TURN so existing
    # callers see no change. Workers (S1) pass a lower value.
    max_steps: int = MAX_STEPS_PER_TURN
    slots: dict[str, Any] = Field(default_factory=dict)
    # Per-turn correlation id (HUG-200). Threaded into every node + tool's
    # structlog contextvars so a `grep request_id=…` reconstructs the
    # whole turn across api/, nl_engine/, and the frontend `client_request_id`
    # ingested via /log.
    request_id: str = ""


class FinalAnswer(BaseModel):
    """Typed payload returned by the `final_answer` terminal tool.

    Every assistant turn ends here. `openui_dsl` is None until HUG-178
    lands; downstream consumers must tolerate it. `mf_query` carries the
    structured MetricFlow call that produced `rows` (when applicable),
    so the UI can render an audit drawer.
    """

    summary: str
    openui_dsl: str | None = None
    rows: list[dict[str, Any]] | None = None
    mf_query: dict[str, Any] | None = None


class ClarifyResult(BaseModel):
    """Returned when the agent invokes the `clarify` tool to terminate
    a turn with a question for the user instead of an answer."""

    question: str
    options: list[str] = Field(default_factory=list)
