"""NL eval runner — scores must-pass + long-tail questions against the
LangGraph agent (Surface 2). Surface 1 was retired in HUG-193, so the
two-path runner collapses to one.

Promotion ledger: when --write-ledger is set, append one row to
.promotion-ledger.csv. The workflow passes --write-ledger only on
main-branch push events.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
import time as _time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from nl_engine.benchmarks.cache import load_cache, save_cache
from nl_engine.benchmarks.grader import (
    GradeResult,
    TierSummary,
    evaluate_gate,
    grade,
    parse_gate_arg,
)
from nl_engine.benchmarks.ledger import (
    LedgerRow,
    accuracy_for,
    append_ledger_row,
)
from nl_engine.benchmarks.runner import (
    agent_path_meaningful,
    agent_to_grader_inputs,
    run_agent,
)
from nl_engine.benchmarks.schema import Question, load_questions
from nl_engine.llm import make_llm

QUESTIONS_FILE = Path(__file__).parent / "questions.yaml"
CACHE_FILE = Path(__file__).parent / ".cache" / "responses.json"
LEDGER_FILE = Path(__file__).parent / ".promotion-ledger.csv"

_DEFAULT_GATE = "must-pass=80,long-tail=65"
_AVG_CALLS_BUDGET = 4.0


@dataclass
class RunOptions:
    gates: dict[str, float]
    write_ledger: bool
    run_id: str
    commit_sha: str
    tier_filter: str = "all"  # "all" | "must-pass" | "long-tail"


def _load_run_inputs(
    opts: RunOptions,
) -> tuple[str, list[Question], BaseChatModel]:
    db_url = os.environ["DATABASE_URL"]
    qf = load_questions(QUESTIONS_FILE)
    questions = qf.questions
    if opts.tier_filter == "must-pass":
        questions = [q for q in questions if q.must_pass]
    elif opts.tier_filter == "long-tail":
        questions = [q for q in questions if not q.must_pass]
    return db_url, questions, make_llm()


def _grade_all_questions(
    questions: list[Question],
    db_url: str,
    llm: BaseChatModel,
    cache: dict[str, dict[str, object]],
) -> tuple[list[GradeResult], list[int]]:
    results_agent: list[GradeResult] = []
    agent_steps: list[int] = []
    total = len(questions)
    run_start = _time.monotonic()
    for idx, q in enumerate(questions, start=1):
        q_start = _time.monotonic()
        tier = "must-pass" if q.must_pass else "long-tail"
        print(  # noqa: T201
            f"[eval] Q{idx}/{total}: {q.id} ({tier}) — {q.question[:80]}",
            flush=True,
        )
        agent_result = run_agent(q, db_url, llm, cache)
        agent_steps.append(agent_result.step_count)
        agent_grade: GradeResult | None = None
        if agent_path_meaningful(q):
            answer_or_clarify, trace = agent_to_grader_inputs(agent_result)
            agent_grade = grade(q, answer_or_clarify, tool_call_trace=trace)
            results_agent.append(agent_grade)
        verdict = "PASS" if (agent_grade and agent_grade.correct) else (
            "FAIL" if agent_grade else "n/a"
        )
        print(  # noqa: T201
            f"[eval] Q{idx}/{total} done — agent={verdict} steps="
            f"{agent_result.step_count} elapsed="
            f"{_time.monotonic() - q_start:.1f}s cumulative="
            f"{_time.monotonic() - run_start:.0f}s",
            flush=True,
        )
    return results_agent, agent_steps


def _emit_signals(
    agent_tiers: list[TierSummary],
    avg_calls: float,
    agent_exit: int,
) -> tuple[float | None, float | None, str]:
    must_pass_agent = accuracy_for(agent_tiers, "must-pass")
    long_tail_agent = accuracy_for(agent_tiers, "long-tail")
    gate_pass = agent_exit == 0 and avg_calls <= _AVG_CALLS_BUDGET
    return (
        must_pass_agent,
        long_tail_agent,
        "PASS" if gate_pass else "FAIL",
    )


def run(opts: RunOptions) -> int:
    db_url, questions, llm = _load_run_inputs(opts)
    cache = load_cache(CACHE_FILE)
    results_agent, agent_steps = _grade_all_questions(
        questions, db_url, llm, cache,
    )
    save_cache(CACHE_FILE, cache)

    agent_exit, agent_tiers = evaluate_gate(results_agent, opts.gates)
    avg_calls = (sum(agent_steps) / len(agent_steps)) if agent_steps else 0.0

    sys.path.insert(0, str(Path(__file__).parent))
    from report import print_agent_report  # noqa: PLC0415

    print_agent_report(
        agent_results=results_agent,
        agent_tiers=agent_tiers,
        avg_calls_per_turn=avg_calls,
        avg_calls_budget=_AVG_CALLS_BUDGET,
    )

    mp_agent, lt_agent, gate_status = _emit_signals(
        agent_tiers, avg_calls, agent_exit,
    )

    if opts.write_ledger:
        append_ledger_row(
            LEDGER_FILE,
            LedgerRow(
                run_id=opts.run_id,
                commit_sha=opts.commit_sha,
                run_date=_dt.datetime.now(_dt.UTC).isoformat(),
                must_pass_agent=mp_agent,
                long_tail_agent=lt_agent,
                agent_avg_calls_per_turn=avg_calls,
                gate_status=gate_status,
            ),
        )

    return agent_exit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NL eval benchmark")
    parser.add_argument(
        "--gate",
        type=str,
        default=_DEFAULT_GATE,
        metavar="STR",
        help=f"Tier thresholds. Default: {_DEFAULT_GATE!r}.",
    )
    parser.add_argument(
        "--write-ledger",
        action="store_true",
        help="Append a row to .promotion-ledger.csv (main-branch CI only).",
    )
    parser.add_argument(
        "--tier",
        type=str,
        default="all",
        choices=("all", "must-pass", "long-tail"),
        help="Which tier of questions to run (default: all).",
    )
    parser.add_argument("--run-id", type=str, default="")
    parser.add_argument("--commit-sha", type=str, default="")
    args = parser.parse_args()
    try:
        gates = parse_gate_arg(args.gate)
    except ValueError as exc:
        parser.error(str(exc))
    sys.exit(
        run(
            RunOptions(
                gates=gates,
                write_ledger=args.write_ledger,
                run_id=args.run_id or str(uuid4()),
                commit_sha=args.commit_sha,
                tier_filter=args.tier,
            )
        )
    )


if __name__ == "__main__":
    main()
