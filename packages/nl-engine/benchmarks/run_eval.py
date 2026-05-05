"""NL eval runner — scores questions against both Surface 1 (engine.ask) and
Surface 2 (the LangGraph agent), per HUG-189.

Two-path rollout: every question runs through both paths. The agent path
is the gating signal; the legacy column is informational and will be
deleted by HUG-193. Long-tail agent grading is intentionally skipped —
see runner.agent_path_meaningful for the rule.

Promotion ledger: when --write-ledger is set, append one row to
.promotion-ledger.csv. The workflow passes --write-ledger only on
main-branch push events.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
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
    run_legacy,
)
from nl_engine.benchmarks.schema import Question, load_questions
from nl_engine.context_loader import load_all

QUESTIONS_FILE = Path(__file__).parent / "questions.yaml"
CACHE_FILE = Path(__file__).parent / ".cache" / "responses.json"
LEDGER_FILE = Path(__file__).parent / ".promotion-ledger.csv"

_DEFAULT_GATE = "must-pass=80,long-tail=65"
_AGENT_LEAD_THRESHOLD_PP = 5.0
_AVG_CALLS_BUDGET = 4.0
_AGENT_MODEL = "qwen/qwen3-32b"  # ADR-0004; mirrors api.services.llm

# Question types in the legacy set are filtered out by default; --full
# includes them. The legacy set is kept for runway-state informational
# scoring of the long-tail; HUG-193 will retire the filter.
_LEGACY_TYPES = frozenset({
    "origination_volume", "approval_rate", "funding_rate",
    "delinquency_rate", "portfolio_balance", "product_mix",
    "channel_mix", "edge_case", "ambiguous",
})


@dataclass
class RunOptions:
    gates: dict[str, float]
    full: bool
    write_ledger: bool
    run_id: str
    commit_sha: str


def _make_eval_llm() -> ChatGroq:
    """Construct the agent LLM. Mirrors api.services.llm.make_agent_llm.

    Inlined here so nl_engine doesn't import from api (layer rule).
    ADR-0004 pins reasoning_format='hidden'.
    """
    return ChatGroq(
        model=_AGENT_MODEL,
        temperature=0,
        reasoning_format="hidden",
    )


def _load_run_inputs(
    opts: RunOptions,
) -> tuple[str, Any, list[Question], BaseChatModel]:
    db_url = os.environ["DATABASE_URL"]
    ctx = load_all()
    qf = load_questions(QUESTIONS_FILE)
    questions = qf.questions
    if not opts.full:
        questions = [q for q in questions if q.question_type not in _LEGACY_TYPES]
    return db_url, ctx, questions, _make_eval_llm()


def _grade_all_questions(
    questions: list[Question],
    db_url: str,
    ctx: Any,
    llm: BaseChatModel,
    cache: dict[str, dict[str, object]],
) -> tuple[list[GradeResult], list[GradeResult], list[int]]:
    results_legacy: list[GradeResult] = []
    results_agent: list[GradeResult] = []
    agent_steps: list[int] = []
    for q in questions:
        legacy_result = run_legacy(q, db_url, ctx, cache)
        results_legacy.append(grade(q, legacy_result))
        agent_result = run_agent(q, db_url, llm, cache)
        agent_steps.append(agent_result.step_count)
        if agent_path_meaningful(q):
            answer_or_clarify, trace = agent_to_grader_inputs(agent_result)
            results_agent.append(
                grade(q, answer_or_clarify, tool_call_trace=trace)
            )
    return results_legacy, results_agent, agent_steps


def _emit_signals(
    legacy_tiers: list[TierSummary],
    agent_tiers: list[TierSummary],
    avg_calls: float,
    agent_exit: int,
) -> tuple[float | None, float | None, float | None, float | None, str]:
    must_pass_legacy = accuracy_for(legacy_tiers, "must-pass")
    must_pass_agent = accuracy_for(agent_tiers, "must-pass")
    long_tail_legacy = accuracy_for(legacy_tiers, "long-tail")
    long_tail_agent = accuracy_for(agent_tiers, "long-tail")
    leading = (
        must_pass_legacy is not None
        and must_pass_agent is not None
        and must_pass_agent >= must_pass_legacy + _AGENT_LEAD_THRESHOLD_PP
    )
    print(f"AGENT_LEADING={'true' if leading else 'false'}")  # noqa: T201
    gate_pass = agent_exit == 0 and avg_calls <= _AVG_CALLS_BUDGET
    return (
        must_pass_legacy,
        must_pass_agent,
        long_tail_legacy,
        long_tail_agent,
        "PASS" if gate_pass else "FAIL",
    )


def run(opts: RunOptions) -> int:
    db_url, ctx, questions, llm = _load_run_inputs(opts)
    cache = load_cache(CACHE_FILE)
    results_legacy, results_agent, agent_steps = _grade_all_questions(
        questions, db_url, ctx, llm, cache,
    )
    save_cache(CACHE_FILE, cache)

    _, legacy_tiers = evaluate_gate(results_legacy, opts.gates)
    agent_exit, agent_tiers = evaluate_gate(results_agent, opts.gates)
    avg_calls = (sum(agent_steps) / len(agent_steps)) if agent_steps else 0.0

    sys.path.insert(0, str(Path(__file__).parent))
    from report import print_two_path_report  # noqa: PLC0415

    print_two_path_report(
        legacy_results=results_legacy,
        agent_results=results_agent,
        legacy_tiers=legacy_tiers,
        agent_tiers=agent_tiers,
        avg_calls_per_turn=avg_calls,
        avg_calls_budget=_AVG_CALLS_BUDGET,
    )

    mp_legacy, mp_agent, lt_legacy, lt_agent, gate_status = _emit_signals(
        legacy_tiers, agent_tiers, avg_calls, agent_exit,
    )

    if opts.write_ledger:
        append_ledger_row(
            LEDGER_FILE,
            LedgerRow(
                run_id=opts.run_id,
                commit_sha=opts.commit_sha,
                run_date=_dt.datetime.now(_dt.UTC).isoformat(),
                must_pass_legacy=mp_legacy,
                must_pass_agent=mp_agent,
                long_tail_legacy=lt_legacy,
                long_tail_agent=lt_agent,
                agent_avg_calls_per_turn=avg_calls,
                gate_status=gate_status,
            ),
        )

    # The agent path is the gating signal (HUG-189 amendment).
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
    parser.add_argument("--full", action="store_true")
    parser.add_argument(
        "--write-ledger",
        action="store_true",
        help="Append a row to .promotion-ledger.csv (main-branch CI only).",
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
                full=args.full,
                write_ledger=args.write_ledger,
                run_id=args.run_id or str(uuid4()),
                commit_sha=args.commit_sha,
            )
        )
    )


if __name__ == "__main__":
    main()
