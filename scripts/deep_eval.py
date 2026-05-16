"""Deep-research eval harness (HUG-248).

Runs the 14-question rubric set at `tests/deep_research/questions.yaml`
through the autonomous lead agent (HUG-244 path, flag forced on) and
scores each answer with an LLM-as-judge against the question's rubric.

Captures per-question artefacts for post-mortem:
  - final_answer summary (+ optional openui_dsl)
  - subagent_calls rows (count + status + per-call summaries)
  - research_plans versions (whether the lead used propose_plan)
  - research_lead_notes (memory writes between subagents)
  - per-mf_query latency (HUG-249 hook — captured here so HUG-249 just
    reads the same artefact)

Outputs:
  - Per-question PASS/FAIL + verdict text from the LLM judge
  - Aggregate pass rate
  - Latency stats (median, p95) per question and overall

Run via:  `make deep-eval`  (or `uv run python scripts/deep_eval.py`)

This script lives outside `packages/nl-engine/` and is NOT named
`eval.py`/`eval_grader.py`, so editing it doesn't trigger the long-
running NL Eval CI workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = REPO_ROOT / "tests" / "deep_research" / "questions.yaml"

# Make the nl-engine + api packages importable.
sys.path.insert(0, str(REPO_ROOT / "packages" / "nl-engine" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "api" / "src"))


def _load_questions() -> list[dict[str, Any]]:
    raw = yaml.safe_load(QUESTIONS_FILE.read_text())
    questions = raw.get("questions", []) if isinstance(raw, dict) else []
    return questions  # type: ignore[no-any-return]


# ── Per-question execution ───────────────────────────────────────────


def _run_one_question(
    question: dict[str, Any],
    db_url: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Run one question end-to-end against the lead agent and return the
    captured artefacts. `dry_run=True` skips the LLM call and returns a
    placeholder — useful for smoke-testing the harness wiring without
    burning tokens."""
    if dry_run:
        return {
            "id": question["id"],
            "skipped": True,
            "reason": "dry_run=True",
        }
    # Lazy imports so `--dry-run` works without these deps.
    from langchain_core.messages import HumanMessage  # noqa: PLC0415
    from nl_engine.agent.graph import build_graph  # noqa: PLC0415
    from nl_engine.agent.memory_context import (  # noqa: PLC0415
        bind_memory_context,
        reset_memory_context,
    )
    from nl_engine.agent.run_context import (  # noqa: PLC0415
        bind_event_emitter,
        reset_event_emitter,
    )
    from nl_engine.agent.state import AgentState  # noqa: PLC0415
    from nl_engine.agent.tools import LEAD_AGENT_TOOLS  # noqa: PLC0415
    from nl_engine.llm.factory import make_llm  # noqa: PLC0415

    thread_id = uuid4()
    events: list[tuple[str, dict[str, Any]]] = []
    mem_tokens = bind_memory_context(uuid4(), db_url, thread_id=thread_id)
    emit_token = bind_event_emitter(
        lambda name, payload: events.append((name, dict(payload)))
    )
    try:
        graph = build_graph(make_llm(), tools=LEAD_AGENT_TOOLS)
        state = AgentState(
            messages=[HumanMessage(content=question["question"])],
            thread_id=str(thread_id),
            max_steps=10,
            request_id=question["id"],
        )
        t0 = time.monotonic()
        result = graph.invoke(state)
        elapsed_s = time.monotonic() - t0
    finally:
        reset_event_emitter(emit_token)
        reset_memory_context(mem_tokens)

    messages = result.get("messages", []) if isinstance(result, dict) else []
    final_answer = _extract_final_answer(messages)
    subagent_count = sum(1 for n, _ in events if n == "research.subagent.completed")
    plan_versions = sum(1 for n, _ in events if n == "research.plan.drafted")
    return {
        "id": question["id"],
        "thread_id": str(thread_id),
        "elapsed_s": round(elapsed_s, 1),
        "final_summary": final_answer.get("summary") if final_answer else None,
        "final_openui_dsl": final_answer.get("openui_dsl") if final_answer else None,
        "subagent_count": subagent_count,
        "plan_versions": plan_versions,
        "events": events,
    }


def _extract_final_answer(messages: list[Any]) -> dict[str, Any] | None:
    """Walk messages backwards to find the final_answer ToolMessage."""
    from langchain_core.messages import ToolMessage  # noqa: PLC0415

    for msg in reversed(messages):
        is_final = (
            isinstance(msg, ToolMessage)
            and getattr(msg, "name", None) == "final_answer"
        )
        if is_final:
            content = msg.content
            if isinstance(content, str):
                try:
                    parsed: Any = json.loads(content)
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return {"summary": content}
            return None
    return None


# ── LLM-as-judge grader ──────────────────────────────────────────────


_GRADER_SYSTEM = (
    "You are an evaluation grader for a credit-union analytics agent. "
    "You will be given a question, a rubric (list of criteria the answer "
    "must satisfy), and the agent's final answer summary. Decide whether "
    "the answer meets EACH rubric criterion. Reply with ONLY a JSON "
    "object of the form {\"per_criterion\": [true/false ...], \"overall\": "
    "true/false, \"rationale\": \"<one-sentence reason>\"}. `overall` is "
    "true iff every per_criterion entry is true."
)


def _grade_one(question: dict[str, Any], artefact: dict[str, Any]) -> dict[str, Any]:
    """Ask the LLM judge to evaluate one question's answer."""
    if artefact.get("skipped"):
        return {"id": question["id"], "skipped": True}
    from langchain_core.messages import HumanMessage, SystemMessage  # noqa: PLC0415
    from nl_engine.llm.factory import make_llm  # noqa: PLC0415

    judge = make_llm()  # uses config/llm.yaml default
    rubric = "\n".join(f"- {r}" for r in question.get("rubric", []))
    answer = artefact.get("final_summary") or "<no final_answer produced>"
    user = (
        f"Question: {question['question']}\n\n"
        f"Rubric:\n{rubric}\n\n"
        f"Agent's final answer:\n{answer}\n\n"
        "Reply with JSON only."
    )
    resp = judge.invoke(
        [SystemMessage(content=_GRADER_SYSTEM), HumanMessage(content=user)]
    )
    raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    parsed = _safe_parse_grader(raw)
    parsed["id"] = question["id"]
    return parsed


def _safe_parse_grader(raw: str) -> dict[str, Any]:
    """LLM judge sometimes wraps JSON in prose; extract the first JSON
    object and parse it. Falls back to a fail verdict on parse error."""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {"overall": False, "rationale": "no JSON in grader output"}
    try:
        return json.loads(raw[start : end + 1])  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {"overall": False, "rationale": "JSON parse failed"}


# ── Reporting ────────────────────────────────────────────────────────


def _print_report(
    verdicts: list[dict[str, Any]], artefacts: list[dict[str, Any]]
) -> int:
    passes = sum(1 for v in verdicts if v.get("overall"))
    skipped = sum(1 for v in verdicts if v.get("skipped"))
    total = len(verdicts) - skipped
    print()  # noqa: T201
    print("=" * 72)  # noqa: T201
    print("Deep-research eval results")  # noqa: T201
    print("=" * 72)  # noqa: T201
    print(f"  Passed: {passes}/{total}    Skipped: {skipped}")  # noqa: T201
    for v in verdicts:
        marker = "✓" if v.get("overall") else ("·" if v.get("skipped") else "✗")
        rationale = v.get("rationale", "")
        print(f"  {marker} {v['id']:8s}  {rationale[:80]}")  # noqa: T201
    # Aggregate latency
    elapsed = [
        a.get("elapsed_s")
        for a in artefacts
        if isinstance(a.get("elapsed_s"), (int, float))
    ]
    if elapsed:
        elapsed_sorted = sorted(elapsed)
        median = elapsed_sorted[len(elapsed_sorted) // 2]
        p95_idx = max(0, int(len(elapsed_sorted) * 0.95) - 1)
        p95 = elapsed_sorted[p95_idx]
        print(  # noqa: T201
            f"\nLatency: median={median:.1f}s  p95={p95:.1f}s "
            f"  n={len(elapsed)}"
        )
    return 0 if passes == total else 1


# ── Entry point ──────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Deep-research eval harness")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip LLM calls; just validate yaml + harness wiring.",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default="",
        help="Comma-separated question IDs to run (e.g., dr-001,dr-002).",
    )
    args = parser.parse_args()

    questions = _load_questions()
    if args.ids:
        allow = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in allow]
    if not questions:
        print("No questions to run.")  # noqa: T201
        return 1

    db_url = os.environ.get("DATABASE_URL", "")
    if not args.dry_run and not db_url:
        print("DATABASE_URL must be set unless --dry-run.")  # noqa: T201
        return 2

    artefacts: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []
    for q in questions:
        print(f"[deep-eval] {q['id']}: {q['question'][:80]}", flush=True)  # noqa: T201
        artefact = _run_one_question(q, db_url, dry_run=args.dry_run)
        artefacts.append(artefact)
        verdict = _grade_one(q, artefact) if not args.dry_run else {
            "id": q["id"], "skipped": True
        }
        verdicts.append(verdict)
    return _print_report(verdicts, artefacts)


if __name__ == "__main__":
    sys.exit(main())
