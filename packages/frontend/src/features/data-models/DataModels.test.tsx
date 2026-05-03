/** @vitest-environment jsdom */
import { fireEvent, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import DataModels from "./DataModels";
import type { GraphResponse, NodeDetail } from "./types";

vi.mock("./api");
import { useGetDataModelGraphQuery, useGetDataModelNodeQuery } from "./api";

vi.mock("./GraphCanvas", () => ({
	default: ({
		nodes,
		onSelect,
	}: {
		nodes: { id: string; name: string }[];
		onSelect: (id: string) => void;
	}) => (
		<div data-testid="graph-canvas">
			{nodes.map((n) => (
				<button
					key={n.id}
					type="button"
					data-testid={`node-${n.id}`}
					onClick={() => onSelect(n.id)}
				>
					{n.name}
				</button>
			))}
		</div>
	),
}));

const GRAPH: GraphResponse = {
	audit_id: "aid",
	generated_at: new Date().toISOString(),
	nodes: [
		{
			id: "source.hughes_ai.raw.booked_loans",
			name: "booked_loans",
			kind: "source",
			layer: "Sources",
			materialization: null,
			description: "Raw loans table",
			nl_query_count_30d: 0,
		},
		{
			id: "model.hughes_ai.fct_loans_monthly",
			name: "fct_loans_monthly",
			kind: "mart",
			layer: "Marts",
			materialization: "table",
			description: "Monthly rollup",
			nl_query_count_30d: 4,
		},
		{
			id: "dashboard.executive",
			name: "Executive Summary",
			kind: "dashboard",
			layer: "Dashboards",
			materialization: null,
			description: "Dashboard at /dashboards/executive",
			nl_query_count_30d: 0,
		},
	],
	edges: [
		{
			source: "source.hughes_ai.raw.booked_loans",
			target: "model.hughes_ai.fct_loans_monthly",
		},
		{
			source: "model.hughes_ai.fct_loans_monthly",
			target: "dashboard.executive",
		},
	],
};

const MART_NODE = GRAPH.nodes[1] as GraphResponse["nodes"][number];
const DETAIL: NodeDetail = {
	...MART_NODE,
	columns: [{ name: "as_of_month", type: "DATE", description: "Month start" }],
	parents: ["source.hughes_ai.raw.booked_loans"],
	children: ["dashboard.executive"],
	dashboards: [
		{
			id: "dashboard.executive",
			name: "Executive Summary",
			route: "/dashboards/executive",
		},
	],
	sql: "SELECT 1",
	file_path: "models/marts/fct_loans_monthly.sql",
	last_run_at: null,
};

function mockGraph(
	overrides: Partial<ReturnType<typeof useGetDataModelGraphQuery>> = {},
) {
	vi.mocked(useGetDataModelGraphQuery).mockReturnValue({
		data: GRAPH,
		isLoading: false,
		isError: false,
		isFetching: false,
		isSuccess: true,
		isUninitialized: false,
		refetch: vi.fn(),
		...overrides,
	} as ReturnType<typeof useGetDataModelGraphQuery>);
}

function mockNode(detail: NodeDetail | undefined = DETAIL) {
	vi.mocked(useGetDataModelNodeQuery).mockReturnValue({
		data: detail,
		isLoading: false,
		isError: false,
		isFetching: false,
		isSuccess: detail !== undefined,
		isUninitialized: detail === undefined,
		refetch: vi.fn(),
	} as ReturnType<typeof useGetDataModelNodeQuery>);
}

function renderPage() {
	return renderWithProviders(
		<MemoryRouter>
			<DataModels />
		</MemoryRouter>,
	);
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("DataModels", () => {
	it("renders all three nodes from the loaded graph", () => {
		mockGraph();
		mockNode(undefined);
		renderPage();
		expect(
			screen.getByTestId("node-source.hughes_ai.raw.booked_loans"),
		).toBeInTheDocument();
		expect(
			screen.getByTestId("node-model.hughes_ai.fct_loans_monthly"),
		).toBeInTheDocument();
		expect(screen.getByTestId("node-dashboard.executive")).toBeInTheDocument();
	});

	it("filtering by dashboard hides nodes outside its ancestor closure", () => {
		mockGraph();
		mockNode(undefined);
		renderPage();
		// Sanity: all 3 nodes visible to start.
		expect(
			screen.getByTestId("node-source.hughes_ai.raw.booked_loans"),
		).toBeInTheDocument();
		// Toggle "All" → keep clicking Executive Summary chip in the FilterBar.
		fireEvent.click(
			screen.getByRole("button", { name: "Executive Summary", pressed: false }),
		);
		// Closure of dashboard.executive includes booked_loans and fct_loans_monthly.
		expect(
			screen.getByTestId("node-source.hughes_ai.raw.booked_loans"),
		).toBeInTheDocument();
		expect(
			screen.getByTestId("node-model.hughes_ai.fct_loans_monthly"),
		).toBeInTheDocument();
		expect(screen.getByTestId("node-dashboard.executive")).toBeInTheDocument();
	});

	it("toggling the Sources layer chip removes source nodes from the graph", () => {
		mockGraph();
		mockNode(undefined);
		renderPage();
		fireEvent.click(
			screen.getByRole("button", { name: "Sources", pressed: true }),
		);
		expect(
			screen.queryByTestId("node-source.hughes_ai.raw.booked_loans"),
		).not.toBeInTheDocument();
		// Marts and Dashboards remain.
		expect(
			screen.getByTestId("node-model.hughes_ai.fct_loans_monthly"),
		).toBeInTheDocument();
	});

	it("clicking a graph node opens the drawer and shows the node name", async () => {
		mockGraph();
		mockNode(DETAIL);
		renderPage();
		fireEvent.click(
			screen.getByTestId("node-model.hughes_ai.fct_loans_monthly"),
		);
		// Mantine Drawer renders the title and body. Title is "fct_loans_monthly".
		const dialog = await screen.findByRole("dialog");
		expect(dialog).toHaveTextContent("fct_loans_monthly");
		expect(dialog).toHaveTextContent("Executive Summary");
		expect(dialog).toHaveTextContent("as_of_month");
	});

	it("renders loading state while graph query is loading", () => {
		mockGraph({ data: undefined, isLoading: true, isSuccess: false });
		mockNode(undefined);
		renderPage();
		expect(screen.getByText("Loading data model…")).toBeInTheDocument();
	});

	it("renders error state when graph query errors", () => {
		mockGraph({
			data: undefined,
			isLoading: false,
			isError: true,
			isSuccess: false,
		});
		mockNode(undefined);
		renderPage();
		expect(
			screen.getByText("Failed to load data model graph."),
		).toBeInTheDocument();
	});
});
