"""Promotion-ledger CSV writer.

Append-only audit trail. Columns (post-HUG-193 / HUG-194 cleanup):
  run_id, commit_sha, run_date, must_pass_agent, long_tail_agent,
  agent_avg_calls_per_turn, gate_status

The original schema also had `must_pass_legacy` / `long_tail_legacy`
columns recording Surface 1's accuracy on the same run. Surface 1 was
retired in HUG-193 and the columns were dropped in this cleanup pass —
no audit-trail need to keep them around.

Empty (None) accuracy values are written as empty strings — they
indicate the tier was empty on this run. Numeric values are rendered
to one decimal place; agent_avg_calls_per_turn to two decimals.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from nl_engine.benchmarks.grader import TierSummary

LEDGER_COLUMNS = (
    "run_id",
    "commit_sha",
    "run_date",
    "must_pass_agent",
    "long_tail_agent",
    "agent_avg_calls_per_turn",
    "gate_status",
)


@dataclass
class LedgerRow:
    run_id: str
    commit_sha: str
    run_date: str
    must_pass_agent: float | None
    long_tail_agent: float | None
    agent_avg_calls_per_turn: float
    gate_status: str  # "PASS" | "FAIL"


def accuracy_for(tiers: list[TierSummary], name: str) -> float | None:
    """Pull the tier's accuracy by name; None if EMPTY (no questions)."""
    for t in tiers:
        if t.name == name:
            return None if t.status == "EMPTY" else t.accuracy
    return None


def _render_pct(v: float | None) -> str:
    return "" if v is None else f"{v:.1f}"


def append_ledger_row(path: Path, row: LedgerRow) -> None:
    """Append one row to .promotion-ledger.csv (creating with header if absent)."""
    is_new = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if is_new:
            writer.writerow(LEDGER_COLUMNS)
        writer.writerow(
            [
                row.run_id,
                row.commit_sha,
                row.run_date,
                _render_pct(row.must_pass_agent),
                _render_pct(row.long_tail_agent),
                f"{row.agent_avg_calls_per_turn:.2f}",
                row.gate_status,
            ]
        )
