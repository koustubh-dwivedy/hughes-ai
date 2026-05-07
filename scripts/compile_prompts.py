"""Compile the agent's DSPy prompts against the labeled eval set.

HUG-181: replace hand-written templates with DSPy-optimized artifacts.
Compilation is opt-in (LLM-heavy) and lands artifacts under
`packages/nl-engine/src/nl_engine/agent/prompts/compiled/`. The agent's
runtime loads them via `prompts.loader.load_compiled`; missing files
fall back to the hand-written signature so the agent always works.

Usage:
    GROQ_API_KEY=... python scripts/compile_prompts.py [--module NAME]

Without `--module`, all five modules compile in sequence. With it, only
the named module compiles (useful for iterating on one signature).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import dspy
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "packages" / "nl-engine" / "src"))

from nl_engine.agent.prompts import (  # noqa: E402
    Clarify,
    MetricFlowQueryWriter,
    PlanQuestion,
    RenderChartSpec,
    Summarize,
)
from nl_engine.agent.prompts.loader import COMPILED_DIR  # noqa: E402

QUESTIONS_YAML = (
    REPO / "packages" / "nl-engine" / "benchmarks" / "questions.yaml"
)


def _load_questions() -> list[dict[str, str]]:
    raw = yaml.safe_load(QUESTIONS_YAML.read_text())
    return list(raw.get("questions", []))


def _build_planquestion_trainset(rows: list[dict[str, str]]) -> list[dspy.Example]:
    """All eval-set rows are queries, so the supervised signal is
    'action == query_data'. The optimizer still tunes few-shot example
    selection + instruction wording on this label."""
    examples = []
    for row in rows:
        ex = dspy.Example(
            question=row["question"],
            available_metrics="",  # filled at runtime; eval-set has none
            conversation_history="",
            action="query_data",
            rationale="The question asks for a metric value.",
        ).with_inputs("question", "available_metrics", "conversation_history")
        examples.append(ex)
    return examples


def _build_summarize_trainset(rows: list[dict[str, str]]) -> list[dspy.Example]:
    """Use ground-truth SQL as a stand-in for what the summary should
    explain. This is the weakest of the five trainsets; the lift it
    produces is a useful signal on whether DSPy is worth keeping."""
    examples = []
    for row in rows:
        ex = dspy.Example(
            rows="[]",
            mf_query=row.get("ground_truth_sql", ""),
            metric_definition="",
            summary=row["question"],
        ).with_inputs("rows", "mf_query", "metric_definition")
        examples.append(ex)
    return examples


def _exact_match(
    example: dspy.Example, pred: dspy.Prediction, trace: object = None
) -> bool:
    """Lightweight metric: did the predicted action match the label."""
    return getattr(pred, "action", None) == example.action


def _configure_lm() -> None:
    """Point DSPy at the active provider. Defaults to Groq."""
    provider = os.environ.get("LLM_PROVIDER", "groq")
    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            sys.exit("GROQ_API_KEY is required to compile against Groq.")
        lm = dspy.LM("groq/qwen/qwen3-32b", api_key=api_key, temperature=0)
    elif provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            sys.exit("GOOGLE_API_KEY is required to compile against Google.")
        lm = dspy.LM("gemini/gemma-4-31b-it", api_key=api_key, temperature=0)
    else:
        sys.exit(f"unknown LLM_PROVIDER={provider}")
    dspy.configure(lm=lm)


_BUILDERS: dict[str, tuple[type, object]] = {
    "plan": (PlanQuestion, _build_planquestion_trainset),
    "mf_query_writer": (MetricFlowQueryWriter, _build_planquestion_trainset),
    "render_chart_spec": (RenderChartSpec, _build_planquestion_trainset),
    "summarize": (Summarize, _build_summarize_trainset),
    "clarify": (Clarify, _build_planquestion_trainset),
}


def compile_module(name: str, rows: list[dict[str, str]]) -> Path:
    cls, builder = _BUILDERS[name]
    trainset = builder(rows)  # type: ignore[operator]
    module = cls()
    print(f"  → compiling {name} against {len(trainset)} examples …")
    optimizer = dspy.BootstrapFewShot(metric=_exact_match, max_bootstrapped_demos=4)
    compiled = optimizer.compile(module, trainset=trainset)
    out = COMPILED_DIR / f"{name}.json"
    compiled.save(str(out))
    print(f"  ← wrote {out.relative_to(REPO)}")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--module", choices=sorted(_BUILDERS.keys()))
    args = p.parse_args()
    _configure_lm()
    rows = _load_questions()
    targets = [args.module] if args.module else list(_BUILDERS.keys())
    for name in targets:
        compile_module(name, rows)
    print("done.")


if __name__ == "__main__":
    main()
