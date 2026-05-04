"""End-to-end test: orchestrator routes scripted tool calls correctly
and reaches `final_answer` for the happy path."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from nl_engine.agent.graph import build_graph
from nl_engine.agent.state import AgentState

from ._fake_llm import FakeChatModel


@tool
def list_metrics() -> list[dict[str, str]]:
    """List metrics."""
    return [{"name": "total_loans", "dimensions": []}]


@tool
def final_answer(
    summary: str,
    rows: list[dict[str, int]] | None = None,
) -> dict[str, object]:
    """Terminal."""
    return {"summary": summary, "rows": rows}


_SCRIPTED = [
    AIMessage(
        content="",
        tool_calls=[{"name": "list_metrics", "args": {}, "id": "c1"}],
    ),
    AIMessage(
        content="",
        tool_calls=[
            {
                "name": "final_answer",
                "args": {
                    "summary": "We have 38 metrics.",
                    "rows": [{"count": 38}],
                },
                "id": "c3",
            }
        ],
    ),
]


def test_react_loop_reaches_final_answer() -> None:
    """LLM emits one tool call then final_answer; the orchestrator
    dispatches each, threads ToolMessages back, and terminates with the
    final_answer payload as the last message."""
    graph = build_graph(
        FakeChatModel(responses=_SCRIPTED),
        tools=[list_metrics, final_answer],
    )
    initial = AgentState(
        messages=[HumanMessage(content="How many metrics do we have?")],
        thread_id="test-thread",
    )
    final = graph.invoke(initial)
    last = final["messages"][-1]
    payload = json.loads(last.content)
    assert payload["summary"] == "We have 38 metrics."
    assert payload["rows"] == [{"count": 38}]
    assert final["step_count"] == 2
