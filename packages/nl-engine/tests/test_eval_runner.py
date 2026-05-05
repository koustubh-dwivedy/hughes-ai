"""In-process eval-runner tests (HUG-189). Uses FakeChatModel to script
the agent's tool-call sequence without hitting Groq or the DB."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from nl_engine.agent.eval_runner import (
    AgentEvalResult,
    _extract_final_payload,
    _extract_tool_call_trace,
    run_agent_question,
)
from nl_engine.agent.graph import build_graph
from nl_engine.agent.state import AgentState

from ._fake_llm import FakeChatModel

# ── Stub tools mirroring the production tool surface ────────────────────────


@tool
def list_metrics() -> list[dict[str, str]]:
    """List metrics."""
    return [{"name": "total_loans", "dimensions": ["branch"]}]


@tool
def mf_query(metric: str, dimensions: list[str] | None = None) -> dict[str, object]:
    """Run a MetricFlow query."""
    return {
        "metric": metric,
        "dimensions": dimensions or [],
        "rows": [{"branch": "Downtown", "total_loans": 42}],
    }


@tool
def final_answer(
    summary: str,
    rows: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Terminal — final answer."""
    return {"summary": summary, "rows": rows}


@tool
def clarify(question: str) -> dict[str, object]:
    """Terminal — clarification question."""
    return {"question": question, "options": []}


_TOOLS = [list_metrics, mf_query, final_answer, clarify]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _invoke_with_script(scripted: list[AIMessage]) -> AgentEvalResult:
    """Drive the graph with a scripted FakeChatModel and return the result.

    Mirrors run_agent_question() but lets us inject our own toolset for
    deterministic testing.
    """
    from uuid import uuid4

    graph = build_graph(FakeChatModel(responses=scripted), tools=_TOOLS)
    initial = AgentState(
        messages=[HumanMessage(content="How many loans by branch?")],
        thread_id=f"test-{uuid4()}",
    )
    final = graph.invoke(initial)
    messages = final["messages"]
    kind, payload = _extract_final_payload(messages)
    rows = list(payload.get("rows") or [])
    columns = list(rows[0].keys()) if rows else []
    return AgentEvalResult(
        rows=rows,
        columns=columns,
        summary=str(payload.get("summary") or payload.get("question") or ""),
        tool_call_trace=_extract_tool_call_trace(messages),
        step_count=int(final.get("step_count") or 0),
        elapsed_seconds=0.0,
        final_message_kind=kind,
    )


# ── Happy path ──────────────────────────────────────────────────────────────


def test_happy_path_list_metrics_then_mf_query_then_final_answer() -> None:
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "list_metrics", "args": {}, "id": "c1"}],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "mf_query",
                    "args": {"metric": "total_loans", "dimensions": ["branch"]},
                    "id": "c2",
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {
                        "summary": "Downtown has 42 loans.",
                        "rows": [{"branch": "Downtown", "total_loans": 42}],
                    },
                    "id": "c3",
                }
            ],
        ),
    ]
    result = _invoke_with_script(scripted)
    assert result.final_message_kind == "final_answer"
    assert result.rows == [{"branch": "Downtown", "total_loans": 42}]
    assert result.columns == ["branch", "total_loans"]
    assert result.summary == "Downtown has 42 loans."
    assert [t["tool"] for t in result.tool_call_trace] == [
        "list_metrics",
        "mf_query",
        "final_answer",
    ]
    assert result.step_count == 3


# ── Clarification path ──────────────────────────────────────────────────────


def test_clarification_path() -> None:
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "list_metrics", "args": {}, "id": "c1"}],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "clarify",
                    "args": {
                        "question": "Did you want auto or mortgage loans?",
                    },
                    "id": "c2",
                }
            ],
        ),
    ]
    result = _invoke_with_script(scripted)
    assert result.final_message_kind == "clarify"
    assert result.rows == []
    assert result.summary == "Did you want auto or mortgage loans?"
    assert [t["tool"] for t in result.tool_call_trace] == [
        "list_metrics",
        "clarify",
    ]


# ── Step-cap path ────────────────────────────────────────────────────────────


def test_step_cap_path_when_agent_never_terminates() -> None:
    """Script an LLM that emits non-terminal tool calls forever; the
    graph hits MAX_STEPS_PER_TURN=10 and routes to step_cap."""
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "list_metrics", "args": {}, "id": f"c{i}"}],
        )
        for i in range(20)  # FakeChatModel re-emits the last entry past length
    ]
    result = _invoke_with_script(scripted)
    assert result.final_message_kind == "step_cap"
    assert result.step_count == 10
    assert len(result.tool_call_trace) >= 10


# ── Trace extraction unit tests ─────────────────────────────────────────────


def test_extract_tool_call_trace_handles_no_tool_calls() -> None:
    msgs = [HumanMessage(content="hi"), AIMessage(content="hello")]
    assert _extract_tool_call_trace(msgs) == []


def test_extract_tool_call_trace_preserves_order_across_multiple_aimessages() -> None:
    msgs = [
        AIMessage(content="", tool_calls=[{"name": "a", "args": {}, "id": "1"}]),
        AIMessage(content="", tool_calls=[{"name": "b", "args": {}, "id": "2"}]),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "c", "args": {}, "id": "3"},
                {"name": "d", "args": {}, "id": "4"},
            ],
        ),
    ]
    assert [t["tool"] for t in _extract_tool_call_trace(msgs)] == ["a", "b", "c", "d"]


# ── run_agent_question signature smoke ──────────────────────────────────────


def test_run_agent_question_invokes_graph_and_returns_typed_result() -> None:
    """Smoke check that the public entry point glues together correctly."""
    scripted = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {"summary": "ok", "rows": [{"x": 1}]},
                    "id": "c1",
                }
            ],
        ),
    ]
    # FakeChatModel doesn't bind tools, so graph routing happens against
    # the production tool registry. The "final_answer" tool name matches.
    result = run_agent_question(
        question="dummy",
        db_url="postgresql://ignored",
        llm=FakeChatModel(responses=scripted),
    )
    assert result.final_message_kind == "final_answer"
    assert result.rows == [{"x": 1}]
    assert result.summary == "ok"
    assert result.elapsed_seconds >= 0.0
