"""Step-cap test: an infinite tool-call loop must terminate at step 10
with a clean apology message instead of a stack trace."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from nl_engine.agent.graph import build_graph
from nl_engine.agent.state import MAX_STEPS_PER_TURN, AgentState

from ._fake_llm import FakeChatModel


@tool
def list_metrics() -> list[str]:
    """Always-callable noop tool used to drive the loop."""
    return []


def test_runaway_loop_terminates_at_step_cap() -> None:
    """The fake LLM emits a non-terminal tool call every turn; the graph
    must terminate at MAX_STEPS_PER_TURN with the apology AIMessage."""
    looping = AIMessage(
        content="",
        tool_calls=[{"name": "list_metrics", "args": {}, "id": "loop"}],
    )
    graph = build_graph(
        FakeChatModel(responses=[looping]),
        tools=[list_metrics],
    )
    initial = AgentState(
        messages=[HumanMessage(content="loop forever")],
        thread_id="step-cap-test",
    )
    final = graph.invoke(initial, config={"recursion_limit": 50})
    assert final["step_count"] == MAX_STEPS_PER_TURN
    last = final["messages"][-1]
    assert isinstance(last, AIMessage)
    assert "couldn't reach an answer" in last.content
    assert str(MAX_STEPS_PER_TURN) in last.content
