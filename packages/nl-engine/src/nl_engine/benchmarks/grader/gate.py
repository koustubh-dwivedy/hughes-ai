"""Tier-aware gate evaluation — must-pass blocks, long-tail warns, empty passes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from nl_engine.benchmarks.grader.grade import GradeResult

TierStatus = Literal["PASS", "FAIL", "WARN", "EMPTY"]

MUST_PASS_TIER = "must-pass"  # noqa: S105 — tier name, not a credential  # nosec B105
LONG_TAIL_TIER = "long-tail"


@dataclass
class TierSummary:
    name: str
    correct: int
    total: int
    accuracy: float
    threshold: float | None
    status: TierStatus
    failures_by_category: dict[str, int] = field(default_factory=dict)


def parse_gate_arg(arg: str) -> dict[str, float]:
    """Parse `'must-pass=80,long-tail=65'` into a {tier: threshold} dict.

    Raises ValueError on malformed input. Whitespace tolerated.
    """
    out: dict[str, float] = {}
    if not arg or not arg.strip():
        raise ValueError("--gate must not be empty")
    for raw_token in arg.split(","):
        token = raw_token.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"--gate token missing '=': {token!r}")
        k, v = token.split("=", 1)
        try:
            out[k.strip()] = float(v.strip())
        except ValueError as exc:
            raise ValueError(f"--gate threshold not a number: {token!r}") from exc
    if not out:
        raise ValueError(f"--gate parsed empty: {arg!r}")
    return out


def _tier_for(result: GradeResult) -> str:
    return MUST_PASS_TIER if result.must_pass else LONG_TAIL_TIER


def _build_summary(
    tier_name: str,
    bucket: list[GradeResult],
    threshold: float | None,
) -> TierSummary:
    total = len(bucket)
    correct = sum(1 for r in bucket if r.correct)
    accuracy = (correct / total * 100) if total else 0.0
    cat_failures: dict[str, int] = {}
    for r in bucket:
        if r.correct:
            continue
        cat_failures[r.category] = cat_failures.get(r.category, 0) + 1
    status: TierStatus
    if total == 0:
        status = "EMPTY"
    elif threshold is None or accuracy >= threshold:
        status = "PASS"
    elif tier_name == MUST_PASS_TIER:
        status = "FAIL"
    else:
        status = "WARN"
    return TierSummary(
        name=tier_name,
        correct=correct,
        total=total,
        accuracy=round(accuracy, 1),
        threshold=threshold,
        status=status,
        failures_by_category=cat_failures,
    )


def evaluate_gate(
    results: list[GradeResult],
    gates: dict[str, float],
) -> tuple[int, list[TierSummary]]:
    """Aggregate by tier and apply the gate.

    Tier rules:
      - must-pass below threshold → status=FAIL, exit 1
      - long-tail below threshold → status=WARN, exit unaffected
      - empty tier (no questions) → status=EMPTY, exit unaffected
      - tier passes threshold → status=PASS

    Returns (exit_code, list[TierSummary]).
    """
    by_tier: dict[str, list[GradeResult]] = {
        MUST_PASS_TIER: [],
        LONG_TAIL_TIER: [],
    }
    for r in results:
        by_tier[_tier_for(r)].append(r)
    summaries: list[TierSummary] = []
    exit_code = 0
    for tier_name in (MUST_PASS_TIER, LONG_TAIL_TIER):
        summary = _build_summary(tier_name, by_tier[tier_name], gates.get(tier_name))
        if summary.status == "FAIL":
            exit_code = 1
        summaries.append(summary)
    return exit_code, summaries
