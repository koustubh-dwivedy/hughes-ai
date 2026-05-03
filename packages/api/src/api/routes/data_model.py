"""Data Model lineage endpoints (read-only).

GET /data-model/graph     — full DAG (sources → staging → core → marts → dashboards)
GET /data-model/nodes/... — detail for a single node, including model SQL

The `{node_id:path}` converter lets dotted dbt unique IDs flow through the URL
without escaping (e.g. `model.hughes_ai.fct_loans_monthly`). If this ever sits
behind a strict proxy that rejects dots, swap to a `?id=...` query param.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from api.repo import data_model as repo_dm
from api.repo.history import save_dashboard_audit
from api.service import data_model_service as svc
from api.types.data_model import GraphResponse, NodeDetail

router = APIRouter(prefix="/data-model")


@router.get("/graph", response_model=GraphResponse)
async def graph(request: Request) -> Response:
    rid: str = request.state.request_id
    db_url: str = request.app.state.db_url
    ctx = request.app.state.ctx

    manifest = repo_dm.load_manifest()
    dashboard_map = repo_dm.load_dashboard_mapping()
    nl_counts = repo_dm.count_nl_queries_per_table(db_url, days=30)

    response = svc.compose_graph(
        manifest=manifest,
        ctx=ctx,
        dashboard_map=dashboard_map,
        nl_counts=nl_counts,
        audit_id=rid,
    )
    save_dashboard_audit("data-model-graph", {}, uuid.UUID(rid), db_url)

    return Response(
        content=response.model_dump_json(),
        media_type="application/json",
        headers={"Cache-Control": "max-age=60, public"},
    )


@router.get("/nodes/{node_id:path}", response_model=NodeDetail)
async def node_detail(node_id: str, request: Request) -> Response:
    rid: str = request.state.request_id
    db_url: str = request.app.state.db_url
    ctx = request.app.state.ctx

    manifest = repo_dm.load_manifest()
    dashboard_map = repo_dm.load_dashboard_mapping()
    nl_counts = repo_dm.count_nl_queries_per_table(db_url, days=30)
    run_results = repo_dm.load_run_results()

    detail = svc.compose_node_detail(
        node_id=node_id,
        manifest=manifest,
        ctx=ctx,
        dashboard_map=dashboard_map,
        nl_counts=nl_counts,
        run_results=run_results,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown node id: {node_id}")

    save_dashboard_audit(
        "data-model-node",
        {"node_id": node_id},
        uuid.UUID(rid),
        db_url,
    )

    return Response(
        content=detail.model_dump_json(),
        media_type="application/json",
        headers={"Cache-Control": "max-age=60, public"},
    )
