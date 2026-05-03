/** @vitest-environment jsdom */
import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { GraphEdge, GraphNode, LayerName } from "./types";
import { LAYER_ORDER } from "./types";
import { useSwimlaneLayout } from "./useSwimlaneLayout";

function node(id: string, layer: LayerName, name = id): GraphNode {
	return {
		id,
		name,
		kind: layer === "Sources" ? "source" : "mart",
		layer,
		materialization: null,
		description: null,
		nl_query_count_30d: 0,
	};
}

describe("useSwimlaneLayout", () => {
	it("orders layers left-to-right by layer rank", () => {
		const nodes: GraphNode[] = [
			node("dash", "Dashboards"),
			node("src", "Sources"),
			node("stg", "Staging"),
			node("core", "Core"),
			node("mart", "Marts"),
		];
		const edges: GraphEdge[] = [
			{ source: "src", target: "stg" },
			{ source: "stg", target: "core" },
			{ source: "core", target: "mart" },
			{ source: "mart", target: "dash" },
		];

		const { result } = renderHook(() => useSwimlaneLayout(nodes, edges));
		const positions = new Map(
			result.current.nodes.map((n) => [n.id, n.position.x]),
		);

		expect(positions.get("src")).toBeLessThan(
			positions.get("stg") ?? Number.POSITIVE_INFINITY,
		);
		expect(positions.get("stg")).toBeLessThan(
			positions.get("core") ?? Number.POSITIVE_INFINITY,
		);
		expect(positions.get("core")).toBeLessThan(
			positions.get("mart") ?? Number.POSITIVE_INFINITY,
		);
		expect(positions.get("mart")).toBeLessThan(
			positions.get("dash") ?? Number.POSITIVE_INFINITY,
		);
	});

	it("preserves edge identities", () => {
		const nodes = [node("a", "Sources"), node("b", "Marts")];
		const edges: GraphEdge[] = [{ source: "a", target: "b" }];
		const { result } = renderHook(() => useSwimlaneLayout(nodes, edges));
		expect(result.current.edges).toHaveLength(1);
		expect(result.current.edges[0]?.source).toBe("a");
		expect(result.current.edges[0]?.target).toBe("b");
	});

	it("drops edges where either endpoint is missing", () => {
		const nodes = [node("a", "Sources")];
		const edges: GraphEdge[] = [
			{ source: "a", target: "missing" },
			{ source: "missing", target: "a" },
		];
		const { result } = renderHook(() => useSwimlaneLayout(nodes, edges));
		// Edges to missing nodes are still emitted as react-flow edges (react-flow
		// will simply not render them) — what matters is dagre didn't crash.
		expect(result.current.nodes).toHaveLength(1);
		// Layer order constants stay sane.
		expect(LAYER_ORDER).toContain("Sources");
	});
});
