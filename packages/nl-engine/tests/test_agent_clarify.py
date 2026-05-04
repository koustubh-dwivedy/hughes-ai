"""Clarify-tool test: when the agent invokes `clarify`, the turn
terminates immediately with the clarification payload as the last
message — no further LLM calls."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from nl_engine.agent.graph import build_graph
from nl_engine.agent.state import AgentState

from ._fake_llm import FakeChatModel


@tool
def clarify(question: str, options: list[str] | None = None) -> dict[str, object]:
    """Terminal clarification."""
    return {"question": question, "options": options or []}


def test_clarify_terminates_turn() -> None:
    scripted = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "clarify",
                    "args": {
                        "question": (
                            "Which metric — delinquency or charge-offs?"
                        ),
                        "options": ["delinquency", "charge-offs"],
                    },
                    "id": "c1",
                }
            ],
        ),
    ]
    graph = build_graph(FakeChatModel(responses=scripted), tools=[clarify])
    initial = AgentState(
        messages=[HumanMessage(content="how bad is it?")],
        thread_id="clarify-test",
    )
    final = graph.invoke(initial)
    assert final["step_count"] == 1
    last = final["messages"][-1]
    payload = json.loads(last.content)
    assert "delinquency" in payload["question"]
    assert payload["options"] == ["delinquency", "charge-offs"]
