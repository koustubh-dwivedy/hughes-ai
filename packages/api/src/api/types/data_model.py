"""Pydantic response models for the Data Model lineage endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NodeKind = Literal["source", "staging", "core", "mart", "dashboard"]
LayerName = Literal["Sources", "Staging", "Core", "Marts", "Dashboards"]


class GraphNode(BaseModel):
    id: str
    name: str
    kind: NodeKind
    layer: LayerName
    materialization: str | None = None
    description: str | None = None
    nl_query_count_30d: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    generated_at: datetime
    audit_id: str


class ColumnInfo(BaseModel):
    name: str
    type: str | None = None
    description: str | None = None


class DashboardLink(BaseModel):
    id: str
    name: str
    route: str


class NodeDetail(GraphNode):
    columns: list[ColumnInfo] = []
    parents: list[str] = []
    children: list[str] = []
    dashboards: list[DashboardLink] = []
    sql: str | None = None
    file_path: str | None = None
    last_run_at: datetime | None = None
