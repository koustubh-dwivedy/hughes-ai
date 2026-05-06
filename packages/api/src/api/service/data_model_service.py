"""Compose the Data Model graph + node detail from manifest + NL counts.

HUG-193 retired Surface 1's prose grounding YAMLs (`schema_context.yaml`).
The graph used to enrich each node's description and column list with the
prose YAML content. After retirement, that source no longer exists, so
descriptions and column metadata come solely from the dbt manifest
(`schema.yml` files in `packages/dbt-models/`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from api.types.data_model import (
    ColumnInfo,
    DashboardLink,
    GraphEdge,
    GraphNode,
    GraphResponse,
    LayerName,
    NodeDetail,
    NodeKind,
)

_LAYER_FROM_FQN: dict[str, tuple[NodeKind, LayerName]] = {
    "staging": ("staging", "Staging"),
    "core": ("core", "Core"),
    "marts": ("mart", "Marts"),
}


def _model_iter(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        n
        for n in manifest.get("nodes", {}).values()
        if n.get("resource_type") == "model"
    ]


def _source_iter(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return list(manifest.get("sources", {}).values())


def _description(node: dict[str, Any]) -> str | None:
    desc = (node.get("description") or "").strip()
    return desc or None


def _source_description(src: dict[str, Any]) -> str:
    desc = (src.get("description") or "").strip()
    if desc:
        return desc
    return f"Raw {src['name']} table from {src.get('source_name', 'source')}"


def _make_source_node(src: dict[str, Any], nl_counts: dict[str, int]) -> GraphNode:
    return GraphNode(
        id=src["unique_id"],
        name=src["name"],
        kind="source",
        layer="Sources",
        materialization=None,
        description=_source_description(src),
        nl_query_count_30d=nl_counts.get(src["name"], 0),
    )


def _make_model_node(
    model: dict[str, Any],
    kind: NodeKind,
    layer: LayerName,
    nl_counts: dict[str, int],
) -> GraphNode:
    return GraphNode(
        id=model["unique_id"],
        name=model["name"],
        kind=kind,
        layer=layer,
        materialization=(model.get("config") or {}).get("materialized"),
        description=_description(model),
        nl_query_count_30d=nl_counts.get(model["name"], 0),
    )


def _make_dashboard_node(dash: dict[str, Any]) -> GraphNode:
    return GraphNode(
        id=dash["id"],
        name=dash["name"],
        kind="dashboard",
        layer="Dashboards",
        materialization=None,
        description=f"Dashboard at {dash['route']}",
        nl_query_count_30d=0,
    )


def compose_graph(
    manifest: dict[str, Any],
    dashboard_map: list[dict[str, Any]],
    nl_counts: dict[str, int],
    audit_id: str,
    generated_at: datetime | None = None,
) -> GraphResponse:
    nodes: list[GraphNode] = [
        _make_source_node(s, nl_counts) for s in _source_iter(manifest)
    ]
    edges: list[GraphEdge] = []

    for model in _model_iter(manifest):
        layer_key = model["fqn"][1] if len(model["fqn"]) > 1 else ""
        kind_layer = _LAYER_FROM_FQN.get(layer_key)
        if not kind_layer:
            continue
        kind, layer = kind_layer
        nodes.append(_make_model_node(model, kind, layer, nl_counts))
        for parent_id in (model.get("depends_on") or {}).get("nodes", []):
            edges.append(GraphEdge(source=parent_id, target=model["unique_id"]))

    name_to_id = {m["name"]: m["unique_id"] for m in _model_iter(manifest)}
    for dash in dashboard_map:
        nodes.append(_make_dashboard_node(dash))
        for backed in dash.get("backed_by", []):
            mid = name_to_id.get(backed)
            if mid:
                edges.append(GraphEdge(source=mid, target=dash["id"]))

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        generated_at=generated_at or datetime.now(UTC),
        audit_id=audit_id,
    )


def _columns_for(node: dict[str, Any]) -> list[ColumnInfo]:
    cols = node.get("columns") or {}
    return [
        ColumnInfo(
            name=c.get("name", key),
            type=c.get("data_type"),
            description=(c.get("description") or "").strip() or None,
        )
        for key, c in cols.items()
    ]


def _children_index(manifest: dict[str, Any]) -> dict[str, list[str]]:
    """Reverse depends_on so we can list children for any node id."""
    out: dict[str, list[str]] = {}
    for n in _model_iter(manifest):
        nid = n["unique_id"]
        for parent in (n.get("depends_on") or {}).get("nodes", []):
            out.setdefault(parent, []).append(nid)
    return out


def _dashboards_for_model(
    model_name: str, dashboard_map: list[dict[str, Any]]
) -> list[DashboardLink]:
    return [
        DashboardLink(id=d["id"], name=d["name"], route=d["route"])
        for d in dashboard_map
        if model_name in d.get("backed_by", [])
    ]


def _classify_table_node(
    node: dict[str, Any],
) -> tuple[NodeKind, LayerName, str | None, str | None] | None:
    """Return (kind, layer, materialization, sql) for a model/source node."""
    if node.get("resource_type") == "source":
        return "source", "Sources", None, None
    layer_key = node["fqn"][1] if len(node.get("fqn", [])) > 1 else ""
    kl = _LAYER_FROM_FQN.get(layer_key)
    if not kl:
        return None
    kind, layer = kl
    materialization = (node.get("config") or {}).get("materialized")
    return kind, layer, materialization, node.get("raw_code")


def _build_table_detail(
    node: dict[str, Any],
    dashboard_map: list[dict[str, Any]],
    nl_counts: dict[str, int],
    run_results: dict[str, datetime],
    children_idx: dict[str, list[str]],
) -> NodeDetail | None:
    classified = _classify_table_node(node)
    if classified is None:
        return None
    kind, layer, materialization, sql = classified
    description = (
        _source_description(node) if kind == "source" else _description(node)
    )
    return NodeDetail(
        id=node["unique_id"],
        name=node["name"],
        kind=kind,
        layer=layer,
        materialization=materialization,
        description=description,
        nl_query_count_30d=nl_counts.get(node["name"], 0),
        columns=_columns_for(node),
        parents=list((node.get("depends_on") or {}).get("nodes", [])),
        children=children_idx.get(node["unique_id"], []),
        dashboards=_dashboards_for_model(node["name"], dashboard_map),
        sql=sql,
        file_path=node.get("original_file_path"),
        last_run_at=run_results.get(node["unique_id"]),
    )


def _build_dashboard_detail(
    dash: dict[str, Any], manifest: dict[str, Any]
) -> NodeDetail:
    backed_ids = [
        manifest["nodes"].get(f"model.hughes_ai.{m}", {}).get("unique_id")
        for m in dash.get("backed_by", [])
    ]
    return NodeDetail(
        id=dash["id"],
        name=dash["name"],
        kind="dashboard",
        layer="Dashboards",
        materialization=None,
        description=f"Dashboard at {dash['route']}",
        nl_query_count_30d=0,
        columns=[],
        parents=[bid for bid in backed_ids if bid],
        children=[],
        dashboards=[
            DashboardLink(id=dash["id"], name=dash["name"], route=dash["route"])
        ],
        sql=None,
        file_path=None,
        last_run_at=None,
    )


def compose_node_detail(
    node_id: str,
    manifest: dict[str, Any],
    dashboard_map: list[dict[str, Any]],
    nl_counts: dict[str, int],
    run_results: dict[str, datetime],
) -> NodeDetail | None:
    node = manifest.get("nodes", {}).get(node_id) or manifest.get(
        "sources", {}
    ).get(node_id)
    if node is not None:
        return _build_table_detail(
            node, dashboard_map, nl_counts, run_results, _children_index(manifest)
        )
    for d in dashboard_map:
        if d["id"] == node_id:
            return _build_dashboard_detail(d, manifest)
    return None
