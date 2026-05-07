"""DSPy-compiled prompt modules for the agent (HUG-181).

Each module wraps an LLM call with a typed DSPy `Signature` so that
`scripts/compile_prompts.py` can search for instruction wordings,
few-shot examples, and chain-of-thought variations against the labeled
eval set in `benchmarks/questions.yaml`.

Compiled artifacts land under `prompts/compiled/<module>.json` and are
loaded at runtime by `load_compiled()`. If an artifact is missing, the
module falls back to its hand-written signature instructions — both the
agent and the eval harness keep working without the optimization step.
"""

from nl_engine.agent.prompts.clarify import Clarify
from nl_engine.agent.prompts.loader import COMPILED_DIR, load_compiled
from nl_engine.agent.prompts.mf_query_writer import MetricFlowQueryWriter
from nl_engine.agent.prompts.plan import PlanQuestion
from nl_engine.agent.prompts.render_chart_spec import RenderChartSpec
from nl_engine.agent.prompts.summarize import Summarize

ALL_MODULES = (
    PlanQuestion,
    MetricFlowQueryWriter,
    RenderChartSpec,
    Summarize,
    Clarify,
)

__all__ = [
    "ALL_MODULES",
    "COMPILED_DIR",
    "Clarify",
    "MetricFlowQueryWriter",
    "PlanQuestion",
    "RenderChartSpec",
    "Summarize",
    "load_compiled",
]
