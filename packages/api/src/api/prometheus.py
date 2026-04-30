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
