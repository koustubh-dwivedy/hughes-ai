export type NodeKind = "source" | "staging" | "core" | "mart" | "dashboard";
export type LayerName = "Sources" | "Staging" | "Core" | "Marts" | "Dashboards";

export interface GraphNode {
	id: string;
	name: string;
	kind: NodeKind;
	layer: LayerName;
	materialization: string | null;
	description: string | null;
	nl_query_count_30d: number;
}

export interface GraphEdge {
	source: string;
	target: string;
}

export interface GraphResponse {
	nodes: GraphNode[];
	edges: GraphEdge[];
	generated_at: string;
	audit_id: string;
}

export interface ColumnInfo {
	name: string;
	type: string | null;
	description: string | null;
}

export interface DashboardLink {
	id: string;
	name: string;
	route: string;
}

export interface NodeDetail extends GraphNode {
	columns: ColumnInfo[];
	parents: string[];
	children: string[];
	dashboards: DashboardLink[];
	sql: string | null;
	file_path: string | null;
	last_run_at: string | null;
}

export const LAYER_ORDER: LayerName[] = [
	"Sources",
	"Staging",
	"Core",
	"Marts",
	"Dashboards",
];
