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
