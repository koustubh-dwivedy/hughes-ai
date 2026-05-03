import dagre from "dagre";
import { useMemo } from "react";
import { Position, type Edge as RFEdge, type Node as RFNode } from "reactflow";
import type { GraphEdge, GraphNode, LayerName } from "./types";
import { LAYER_ORDER } from "./types";

const NODE_WIDTH = 200;
const NODE_HEIGHT = 64;

interface LayoutResult {
	nodes: RFNode[];
	edges: RFEdge[];
}

function topoHash(nodes: GraphNode[], edges: GraphEdge[]): string {
	const ids = nodes
		.map((n) => `${n.id}:${n.layer}`)
		.sort()
		.join("|");
	const es = edges
		.map((e) => `${e.source}->${e.target}`)
		.sort()
		.join("|");
	return `${ids}::${es}`;
}

function layerRank(layer: LayerName): number {
	return LAYER_ORDER.indexOf(layer);
}

export function useSwimlaneLayout(
	nodes: GraphNode[],
	edges: GraphEdge[],
): LayoutResult {
	const hash = topoHash(nodes, edges);
	// biome-ignore lint/correctness/useExhaustiveDependencies: hash captures topology; recomputing on every render would be wasteful
	return useMemo(() => layout(nodes, edges), [hash]);
}

function layout(nodes: GraphNode[], edges: GraphEdge[]): LayoutResult {
	const g = new dagre.graphlib.Graph();
	g.setGraph({
		rankdir: "LR",
		nodesep: 32,
		ranksep: 140,
		marginx: 24,
		marginy: 24,
	});
	g.setDefaultEdgeLabel(() => ({}));

	for (const n of nodes) {
		g.setNode(n.id, {
			width: NODE_WIDTH,
			height: NODE_HEIGHT,
			rank: layerRank(n.layer),
		});
	}
	for (const e of edges) {
		if (g.hasNode(e.source) && g.hasNode(e.target)) {
			g.setEdge(e.source, e.target);
		}
	}
	dagre.layout(g);

	const positionedNodes: RFNode[] = nodes.map((n) => {
		const p = g.node(n.id);
		const x = p ? p.x - NODE_WIDTH / 2 : layerRank(n.layer) * 280;
		const y = p ? p.y - NODE_HEIGHT / 2 : 0;
		return {
			id: n.id,
			type: "layer",
			position: { x, y },
			data: n,
			sourcePosition: Position.Right,
			targetPosition: Position.Left,
		};
	});

	const rfEdges: RFEdge[] = edges.map((e, idx) => ({
		id: `e${idx}-${e.source}->${e.target}`,
		source: e.source,
		target: e.target,
		type: "smoothstep",
		animated: false,
	}));

	return { nodes: positionedNodes, edges: rfEdges };
}
