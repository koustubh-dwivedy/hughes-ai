"""Pure-function eval grader (HUG-188).

Two grading paths:
  1. Primary — `ground_truth_rows` set: row-set + column-set match.
  2. Fallback — long-tail without ground truth: structural similarity
     (table equivalence + keyword fraction).

The categorizer surfaces *why* a question failed so HUG-190's tuning loop
can triage. `mf_unsupported` separates semantic-layer gaps from model
failures (detected from the agent path's tool-call trace).

All helpers are pure: no I/O, no external calls.
"""

from nl_engine.benchmarks.grader.categorize import CategoryOutcome, categorize
from nl_engine.benchmarks.grader.gate import (
    TierStatus,
    TierSummary,
    evaluate_gate,
    parse_gate_arg,
)
from nl_engine.benchmarks.grader.grade import GradeResult, grade
from nl_engine.benchmarks.grader.match import (
    columnset_match,
    keyword_frac,
    rowset_match,
    table_equivalence,
)

__all__ = [
    "CategoryOutcome",
    "GradeResult",
    "TierStatus",
    "TierSummary",
    "categorize",
    "columnset_match",
    "evaluate_gate",
    "grade",
    "keyword_frac",
    "parse_gate_arg",
    "rowset_match",
    "table_equivalence",
]
