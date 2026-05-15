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

# ── Research-agent telemetry (HUG-207, deep-research feature) ──────────
# Counters land here so every research phase (planner, executor, worker,
# verifier) imports from one module. Structlog events go through
# `research_agent.telemetry.log_event` which increments the
# self-counter below, giving us a single place to ask "did event X
# fire?" without parsing logs.

research_turns_total = Counter(
    "hughes_research_turns_total",
    "Research turns by route. 'shallow' = today's ReAct path; 'deep' = lead+subagents.",
    ["route"],
    registry=REGISTRY,
)

research_plan_versions_total = Counter(
    "hughes_research_plan_versions_total",
    "Plan rows written. Each re-plan increments this — re-plan rate signal.",
    registry=REGISTRY,
)

research_plan_decisions_total = Counter(
    "hughes_research_plan_decisions_total",
    "User decisions on plan-preview ('approved' or 'aborted').",
    ["decision"],
    registry=REGISTRY,
)

research_steps_total = Counter(
    "hughes_research_steps_total",
    "Step status transitions by terminal state.",
    ["status"],
    registry=REGISTRY,
)

research_subagent_spawns_total = Counter(
    "hughes_research_subagent_spawns_total",
    "Workers spawned by the coordinator.",
    registry=REGISTRY,
)

research_telemetry_events_total = Counter(
    "hughes_research_telemetry_events_total",
    "Self-counter: every research event emitted via telemetry.log_event.",
    ["event_name"],
    registry=REGISTRY,
)

research_turn_duration_seconds = Histogram(
    "hughes_research_turn_duration_seconds",
    "Wall-clock time for a complete research turn (submit → final answer).",
    registry=REGISTRY,
    buckets=(5, 15, 30, 60, 120, 300, 600, 1200, 1800),
)

research_step_duration_seconds = Histogram(
    "hughes_research_step_duration_seconds",
    "Wall-clock time per research step (worker dispatch → finding persisted).",
    registry=REGISTRY,
    buckets=(1, 5, 15, 30, 60, 120, 300, 600),
)

research_plan_size_steps = Histogram(
    "hughes_research_plan_size_steps",
    "Number of steps in a drafted plan.",
    registry=REGISTRY,
    buckets=(1, 2, 3, 5, 8, 13, 21, 34),
)

# HUG-218 (S2): observed batch size when the parallel coordinator
# dispatches a wave of ready (dependency-clear) steps via
# asyncio.gather. Capped by max_parallel=3 default.
research_parallel_batch_size = Histogram(
    "hughes_research_parallel_batch_size",
    "Number of steps dispatched concurrently in one parallel batch.",
    registry=REGISTRY,
    buckets=(1, 2, 3, 4, 5, 8, 13),
)

research_subagent_tokens = Histogram(
    "hughes_research_subagent_tokens",
    "Token count consumed per worker invocation (lead+subagent cost tracking).",
    registry=REGISTRY,
    buckets=(500, 1000, 2500, 5000, 10000, 25000, 50000, 100000),
)

research_lead_note_chars = Histogram(
    "hughes_research_lead_note_chars",
    "Character count of each lead-note version (caps signal external memory bloat).",
    registry=REGISTRY,
    buckets=(500, 1000, 2500, 5000, 10000, 25000, 50000),
)
