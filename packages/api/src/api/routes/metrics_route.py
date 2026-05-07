"""GET /metrics — Prometheus text exposition.

Merges the api-layer registry (route counters, dashboard metrics, agent
turn-level metrics) with `nl_engine.agent.metrics`'s default global
registry (per-step, per-tool, LLM retry, step-cap counters) so a single
scrape sees everything the application emits. HUG-200 introduced the
nl_engine-side registry to avoid the agent layer importing the api
layer (layer boundary).
"""

from fastapi import APIRouter
from fastapi.responses import Response
from nl_engine.agent.metrics import get_default_registry
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.prometheus import REGISTRY

router = APIRouter()


@router.get("/metrics")
def metrics() -> Response:
    api_text = generate_latest(REGISTRY)
    agent_text = generate_latest(get_default_registry())
    return Response(api_text + agent_text, media_type=CONTENT_TYPE_LATEST)
