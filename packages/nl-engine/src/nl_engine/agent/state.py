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
MAX_STEPS_PER_TURN = 10


class AgentState(BaseModel):
    """The full state object the LangGraph instance threads through nodes.

    `messages` is reduced by langgraph's add_messages so each node can
    return new messages without manually copying the prior list.
    """

    model_config = {"arbitrary_types_allowed": True}

    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    thread_id: str
    step_count: int = 0
    slots: dict[str, Any] = Field(default_factory=dict)


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
