"""Prometheus counters/histograms emitted from inside the agent.

Lives inside `nl_engine/` so the agent's graph + tools (which can't
import the `api/` package) have a metrics surface to write to. The
api layer's `/metrics` endpoint exposes BOTH its own registry and
this module's `prometheus_client` default global registry — see
`api/routes/metrics_route.py` after HUG-200.

Naming convention follows the api-side: `hughes_agent_*` for everything
emitted by the agent, distinct from `query_*` (Surface 1 era) and
`dashboard_*` (route-layer). All histograms use buckets sized to the
agent's actual operating envelope, not Prometheus defaults.
"""

from __future__ import annotations

from prometheus_client import REGISTRY as _DEFAULT_REGISTRY
from prometheus_client import CollectorRegistry, Counter, Histogram

# We deliberately register against the default global registry so any
# tests / scripts that import the agent see the same metric instances
# without needing dependency injection. The api `/metrics` route merges
# this registry with its own.
agent_step_duration_seconds = Histogram(
    "hughes_agent_step_duration_seconds",
    "Wall-clock time per agent LLM step.",
    registry=_DEFAULT_REGISTRY,
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

agent_tool_calls_total = Counter(
    "hughes_agent_tool_calls_total",
    "Total tool invocations by name (list_metrics, mf_query, final_answer, ...).",
    ["tool"],
    registry=_DEFAULT_REGISTRY,
)

agent_tool_duration_seconds = Histogram(
    "hughes_agent_tool_duration_seconds",
    "Wall-clock time per tool invocation, labeled by tool name.",
    ["tool"],
    registry=_DEFAULT_REGISTRY,
    buckets=(0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60),
)

agent_llm_retries_total = Counter(
    "hughes_agent_llm_retries_total",
    "Times the agent retried an LLM call due to a transient error.",
    ["reason"],
    registry=_DEFAULT_REGISTRY,
)

agent_step_cap_hits_total = Counter(
    "hughes_agent_step_cap_hits_total",
    "Turns that hit MAX_STEPS_PER_TURN without producing a final_answer.",
    registry=_DEFAULT_REGISTRY,
)


def get_default_registry() -> CollectorRegistry:
    """Expose the registry these counters live on so the api `/metrics`
    route can merge it with its own."""
    return _DEFAULT_REGISTRY
