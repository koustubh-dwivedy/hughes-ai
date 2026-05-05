"""Audit gate: every must-pass question's `expected_metric` must exist
in MetricFlow's semantic catalog (HUG-191).

Why: HUG-188's grader and HUG-189's agent path both rely on
`expected_metric` to score a question via row-set match. If a must-pass
question references a metric not present in MetricFlow's catalog, the
agent will fail it deterministically — no prompt tuning can rescue it.
Catching the gap in the audit tier (cheap, no DB, no LLM) is strictly
preferable to discovering it as an agent-eval failure.

Source of truth: `packages/dbt-models/models/semantic/metrics.yml` —
parsed directly, mirroring the pattern in `test_metricflow_catalog.py`.
This avoids requiring the `mf` CLI + a seeded DB just to verify a name
exists. The risk of YAML-vs-runtime drift is bounded — dbt parses the
same file the `mf` CLI reads.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from nl_engine.benchmarks.schema import Question, load_questions

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUESTIONS_FILE = (
    _REPO_ROOT / "packages" / "nl-engine" / "benchmarks" / "questions.yaml"
)
_MF_METRICS_FILE = (
    _REPO_ROOT / "packages" / "dbt-models" / "models" / "semantic" / "metrics.yml"
)

_RESOLUTION_HINT = (
    "Resolution: either (a) add a semantic-model entry for the missing "
    "metric in packages/dbt-models/models/semantic/, or (b) reclassify "
    "the question as long-tail by setting `must_pass: false`. No third "
    "option — must-pass questions whose metrics MetricFlow doesn't know "
    "are deterministic agent-path failures, not prompt-tuning problems."
)


def _mf_metric_names() -> set[str]:
    raw = yaml.safe_load(_MF_METRICS_FILE.read_text())
    return {m["name"] for m in raw["metrics"]}


def _must_pass_questions() -> list[Question]:
    return [q for q in load_questions(_QUESTIONS_FILE).questions if q.must_pass]


def test_every_must_pass_metric_is_in_metricflow() -> None:
    """For each non-ambiguous must-pass question, expected_metric must be
    a real metric name in MetricFlow's catalog.
    """
    available = _mf_metric_names()
    violations: list[str] = []
    for q in _must_pass_questions():
        if q.question_type == "ambiguous":
            continue  # ambiguous tests the clarify path, no metric
        if not q.expected_metric:
            violations.append(
                f"{q.id}: must-pass question lacks expected_metric "
                "(required for the agent grader)"
            )
            continue
        if q.expected_metric not in available:
            violations.append(
                f"{q.id}: expected_metric={q.expected_metric!r} not in "
                "MetricFlow catalog"
            )
    assert not violations, (
        "must-pass MetricFlow coverage gaps:\n  "
        + "\n  ".join(violations)
        + f"\n\n{_RESOLUTION_HINT}"
    )


def test_must_pass_metric_set_summary() -> None:
    """Documents the must-pass metric coverage as a single line of test
    output. Always passes; serves as a discoverable summary so reviewers
    see at a glance which metrics the gate currently relies on.
    """
    metrics_used = sorted({
        q.expected_metric or ""
        for q in _must_pass_questions()
        if q.expected_metric
    })
    print(  # noqa: T201
        f"\nmust-pass metrics in use ({len(metrics_used)}): "
        + ", ".join(metrics_used)
    )
