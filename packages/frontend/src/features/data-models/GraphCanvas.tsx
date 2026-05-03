import { useMemo } from "react";
import ReactFlow, {
	Background,
	Controls,
	MiniMap,
	ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import LayerNode from "./LayerNode";
import { LAYER_STYLES } from "./layerStyles";
import type { GraphNode, LayerName } from "./types";
import { useSwimlaneLayout } from "./useSwimlaneLayout";

export interface CanvasNode extends GraphNode {
	dimmed?: boolean;
	highlighted?: boolean;
}

interface Props {
	nodes: CanvasNode[];
	edges: { source: string; target: string }[];
	selectedId: string | null;
	onSelect: (id: string | null) => void;
}

const nodeTypes = { layer: LayerNode };

function GraphCanvasInner({ nodes, edges, selectedId, onSelect }: Props) {
	const layout = useSwimlaneLayout(nodes, edges);

	const styledNodes = useMemo(
		() =>
			layout.nodes.map((n) => ({
				...n,
				selected: n.id === selectedId,
			})),
		[layout.nodes, selectedId],
	);

	const miniMapColor = (n: { data: GraphNode }): string =>
		LAYER_STYLES[n.data.layer].accent;

	return (
		<div
			style={{ flex: 1, height: "100%", minHeight: 480, position: "relative" }}
		>
			<ReactFlow
				nodes={styledNodes}
				edges={layout.edges}
				nodeTypes={nodeTypes}
				onNodeClick={(_, node) => onSelect(node.id)}
				onPaneClick={() => onSelect(null)}
				fitView
				panOnScroll
				zoomOnPinch
				proOptions={{ hideAttribution: true }}
				nodesDraggable={false}
				nodesConnectable={false}
				elementsSelectable
			>
				<Background gap={24} size={1} />
				<MiniMap
					pannable
					zoomable
					nodeColor={miniMapColor as (n: unknown) => string}
				/>
				<Controls showInteractive={false} />
			</ReactFlow>
		</div>
	);
}

export default function GraphCanvas(props: Props) {
	return (
		<ReactFlowProvider>
			<GraphCanvasInner {...props} />
		</ReactFlowProvider>
	);
}

export function buildEnabledLayerSet(layers: LayerName[]): Set<LayerName> {
	return new Set<LayerName>(layers);
}
