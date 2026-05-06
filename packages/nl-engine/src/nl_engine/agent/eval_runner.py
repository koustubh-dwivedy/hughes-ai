"""In-process LangGraph agent invocation for the eval harness (HUG-189).

Bypasses the SSE / threads / PostgresSaver layer used by the production
agent_runner.py. Returns a typed result the eval grader can consume:
rows + columns from `final_answer.rows`, the tool-call trace (so HUG-188's
categorizer can detect `mf_unsupported`), and step_count + elapsed_seconds
for the avg-calls-per-turn signal recorded in the promotion ledger.

Uses LangGraph's default in-memory MemorySaver — no Postgres dependency.
The agent's `mf_query` tool will hit the live DB via the `mf` CLI
subprocess, so a seeded database + dbt build are required by the caller.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from nl_engine.agent.graph import build_graph
from nl_engine.agent.state import AgentState

_TERMINAL_TOOLS = {"final_answer", "clarify"}


@dataclass
class AgentEvalResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    summary: str = ""
    tool_call_trace: list[dict[str, Any]] = field(default_factory=list)
    step_count: int = 0
    elapsed_seconds: float = 0.0
    final_message_kind: str = "unknown"  # final_answer | clarify | step_cap | unknown


def _extract_tool_call_trace(messages: list[Any]) -> list[dict[str, Any]]:
    """Walk the message list in order, recording each tool call by name."""
    trace: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                trace.append({"tool": call["name"]})
    return trace


# Cap each printed field so a 20K-token tool-call-result doesn't drown the
# terminal. Full content stays in the cache; this is just for live triage.
_TRACE_CONTENT_CAP = 1200


def _truncate(text: str, cap: int = _TRACE_CONTENT_CAP) -> str:
    if len(text) <= cap:
        return text
    return f"{text[:cap]}… [truncated {len(text) - cap} chars]"


def _print_react_trace(messages: list[Any]) -> None:
    """Dump each ReAct step (AIMessage + ToolMessage pair) for `EVAL_TRACE=1`.

    Shows what the LLM said before each tool call (`.content`), which tool
    it picked with what args (`.tool_calls`), and what came back from the
    tool (`ToolMessage.content`). Skipped silently unless the env var is
    set so normal eval runs stay quiet.
    """
    if os.environ.get("EVAL_TRACE") != "1":
        return
    print("[trace] ─── ReAct trace begin ───", flush=True)  # noqa: T201
    step = 0
    for msg in messages:
        if isinstance(msg, HumanMessage):
            print(  # noqa: T201
                f"[trace] USER: {_truncate(str(msg.content))}", flush=True,
            )
        elif isinstance(msg, AIMessage):
            step += 1
            content = str(msg.content or "").strip()
            if content:
                print(  # noqa: T201
                    f"[trace] step {step} LLM thought: {_truncate(content)}",
                    flush=True,
                )
            if msg.tool_calls:
                for call in msg.tool_calls:
                    args_str = json.dumps(call.get("args", {}), default=str)
                    print(  # noqa: T201
                        f"[trace] step {step} tool_call: {call['name']}"
                        f"({_truncate(args_str)})",
                        flush=True,
                    )
            elif not content:
                print(  # noqa: T201
                    f"[trace] step {step} LLM: (empty)", flush=True,
                )
        elif isinstance(msg, ToolMessage):
            print(  # noqa: T201
                f"[trace] step {step} tool_result {msg.name}: "
                f"{_truncate(str(msg.content))}",
                flush=True,
            )
    print("[trace] ─── ReAct trace end ───", flush=True)  # noqa: T201


def _parse_payload(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _extract_final_payload(messages: list[Any]) -> tuple[str, dict[str, Any]]:
    """Identify the terminating message and parse its payload.

    Returns (kind, payload) where kind is one of:
      - "final_answer" — last message is a ToolMessage from the final_answer tool.
      - "clarify"      — last message is a ToolMessage from the clarify tool.
      - "step_cap"     — last message is the step-cap apology AIMessage.
      - "unknown"      — anything else (graph terminated without a recognized end).
    """
    if not messages:
        return "unknown", {}
    last = messages[-1]
    if isinstance(last, ToolMessage) and last.name in _TERMINAL_TOOLS:
        return last.name, _parse_payload(last.content)
    if isinstance(last, AIMessage) and not last.tool_calls:
        return "step_cap", {}
    return "unknown", {}


def run_agent_question(
    question: str,
    db_url: str,
    llm: BaseChatModel,
) -> AgentEvalResult:
    """Run one question through the agent in-process. Returns a typed result.

    `db_url` is accepted for parity with `engine.ask` but the agent does
    not consume it directly — `mf_query` reads `dbt-models/profiles.yml`
    for the connection string. Keeping the parameter avoids a Surface 1
    vs Surface 2 API divergence in run_eval.py.
    """
    del db_url  # noqa: F841 — see docstring; here for API parity.
    graph = build_graph(llm)
    initial = AgentState(
        messages=[HumanMessage(content=question)],
        thread_id=f"eval-{uuid4()}",
    )
    t0 = time.monotonic()
    final = graph.invoke(initial)
    elapsed = time.monotonic() - t0
    messages = final["messages"]
    _print_react_trace(messages)
    kind, payload = _extract_final_payload(messages)
    rows = list(payload.get("rows") or [])
    columns = list(rows[0].keys()) if rows else []
    return AgentEvalResult(
        rows=rows,
        columns=columns,
        summary=str(payload.get("summary") or payload.get("question") or ""),
        tool_call_trace=_extract_tool_call_trace(messages),
        step_count=int(final.get("step_count") or 0),
        elapsed_seconds=elapsed,
        final_message_kind=kind,
    )
