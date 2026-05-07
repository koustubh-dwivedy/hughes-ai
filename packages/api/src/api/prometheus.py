"""Prometheus metrics registry and counters/histograms for the API."""

from prometheus_client import CollectorRegistry, Counter, Histogram

REGISTRY = CollectorRegistry()

query_total = Counter(
    "query_total",
    "Total NL queries by status",
    ["status"],
    registry=REGISTRY,
)

query_duration_seconds = Histogram(
    "query_duration_seconds",
    "Query duration in seconds by pipeline stage",
    ["stage"],
    registry=REGISTRY,
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed by model",
    ["model"],
    registry=REGISTRY,
)

dashboard_request_total = Counter(
    "dashboard_request_total",
    "Total dashboard requests by endpoint and status",
    ["endpoint", "status"],
    registry=REGISTRY,
)

dashboard_duration_seconds = Histogram(
    "dashboard_duration_seconds",
    "Dashboard request duration in seconds by endpoint",
    ["endpoint"],
    registry=REGISTRY,
)

dashboard_cache_total = Counter(
    "dashboard_cache_total",
    "Dashboard cache hits and misses by endpoint",
    ["endpoint", "result"],
    registry=REGISTRY,
)

# ── Agent telemetry (HUG-200, api-layer counters) ───────────────────────────
# Counters that fire from inside the agent itself (per-step, per-tool,
# retries, step-cap) live in `nl_engine/agent/metrics.py` against the
# default prometheus_client registry — `nl_engine` cannot import this
# module without crossing the layer boundary. The /metrics route merges
# both registries on response.

agent_turn_duration_seconds = Histogram(
    "hughes_agent_turn_duration_seconds",
    "Wall-clock time for a complete user turn (user content -> final SSE).",
    registry=REGISTRY,
    buckets=(1, 5, 15, 30, 60, 120, 300, 600),
)

agent_steps_per_turn = Histogram(
    "hughes_agent_steps_per_turn",
    "Number of LLM steps in a completed turn (capped at MAX_STEPS_PER_TURN).",
    registry=REGISTRY,
    buckets=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
)

agent_error_frames_total = Counter(
    "hughes_agent_error_frames_total",
    "SSE error frames emitted to the client by the producer.",
    registry=REGISTRY,
)
