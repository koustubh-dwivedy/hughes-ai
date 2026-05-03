import { useMemo, useReducer } from "react";
import { colors, spacing, typography } from "../../theme/tokens";
import FilterBar, { type FilterState } from "./FilterBar";
import GraphCanvas, { type CanvasNode } from "./GraphCanvas";
import NodeDetailDrawer from "./NodeDetailDrawer";
import { useGetDataModelGraphQuery } from "./api";
import type { GraphNode, LayerName } from "./types";
import { LAYER_ORDER } from "./types";

interface UIState extends FilterState {
	selectedId: string | null;
}

type Action =
	| { type: "toggle-layer"; layer: LayerName }
	| { type: "set-dashboard"; id: string | null }
	| { type: "select"; id: string | null };

function initialState(): UIState {
	return {
		enabledLayers: new Set<LayerName>(LAYER_ORDER),
		dashboardId: null,
		selectedId: null,
	};
}

function reducer(state: UIState, action: Action): UIState {
	switch (action.type) {
		case "toggle-layer": {
			const next = new Set(state.enabledLayers);
			if (next.has(action.layer)) next.delete(action.layer);
			else next.add(action.layer);
			return { ...state, enabledLayers: next };
		}
		case "set-dashboard":
			return { ...state, dashboardId: action.id };
		case "select":
			return { ...state, selectedId: action.id };
	}
}

function buildParentIndex(
	edges: { source: string; target: string }[],
): Map<string, string[]> {
	const parents = new Map<string, string[]>();
	for (const e of edges) {
		const list = parents.get(e.target) ?? [];
		list.push(e.source);
		parents.set(e.target, list);
	}
	return parents;
}

function ancestorClosure(
	rootId: string,
	edges: { source: string; target: string }[],
): Set<string> {
	const parents = buildParentIndex(edges);
	const visited = new Set<string>([rootId]);
	const stack: string[] = [rootId];
	while (stack.length > 0) {
		const id = stack.pop() as string;
		for (const p of parents.get(id) ?? []) {
			if (!visited.has(p)) {
				visited.add(p);
				stack.push(p);
			}
		}
	}
	return visited;
}

function deriveCanvasNodes(
	nodes: GraphNode[],
	edges: { source: string; target: string }[],
	state: UIState,
): { nodes: CanvasNode[]; edges: { source: string; target: string }[] } {
	const layerOk = (n: GraphNode) => state.enabledLayers.has(n.layer);
	const dashboardSet = state.dashboardId
		? ancestorClosure(state.dashboardId, edges)
		: null;

	const visibleIds = new Set<string>(
		nodes
			.filter(
				(n) => layerOk(n) && (dashboardSet === null || dashboardSet.has(n.id)),
			)
			.map((n) => n.id),
	);

	const canvasNodes: CanvasNode[] = nodes
		.filter((n) => visibleIds.has(n.id))
		.map((n) => ({ ...n }));

	const visibleEdges = edges.filter(
		(e) => visibleIds.has(e.source) && visibleIds.has(e.target),
	);
	return { nodes: canvasNodes, edges: visibleEdges };
}

const layoutStyle: React.CSSProperties = {
	// AppLayout's <main> is position:relative; absolute inset:0 fills its
	// padding-box edge-to-edge, ignoring its 2rem padding so the DAG owns
	// the full pane and never overflows.
	position: "absolute",
	inset: 0,
	display: "flex",
	flexDirection: "column",
	overflow: "hidden",
};

const stateMessageStyle: React.CSSProperties = {
	padding: spacing[8],
	color: colors.slate[600],
	fontSize: typography.size.sm,
	textAlign: "center",
};

export default function DataModels() {
	const [state, dispatch] = useReducer(reducer, undefined, initialState);
	const { data, isLoading, isError } = useGetDataModelGraphQuery();

	const dashboards = useMemo(
		() =>
			(data?.nodes ?? [])
				.filter((n) => n.kind === "dashboard")
				.map((n) => ({ id: n.id, name: n.name, route: "" })),
		[data?.nodes],
	);

	const derived = useMemo(
		() =>
			data
				? deriveCanvasNodes(data.nodes, data.edges, state)
				: { nodes: [], edges: [] },
		[data, state],
	);

	return (
		<div style={layoutStyle}>
			<FilterBar
				state={state}
				dashboards={dashboards}
				onToggleLayer={(layer) => dispatch({ type: "toggle-layer", layer })}
				onSelectDashboard={(id) => dispatch({ type: "set-dashboard", id })}
			/>
			{isLoading && <p style={stateMessageStyle}>Loading data model…</p>}
			{isError && (
				<p style={stateMessageStyle}>Failed to load data model graph.</p>
			)}
			{data !== undefined && !isError && (
				<div style={{ flex: 1, display: "flex", minHeight: 0 }}>
					<GraphCanvas
						nodes={derived.nodes}
						edges={derived.edges}
						selectedId={state.selectedId}
						onSelect={(id) => dispatch({ type: "select", id })}
					/>
				</div>
			)}
			<NodeDetailDrawer
				nodeId={state.selectedId}
				onClose={() => dispatch({ type: "select", id: null })}
				onJumpTo={(id) => dispatch({ type: "select", id })}
			/>
		</div>
	);
}
