import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import ResultPanel from "../features/chat/ResultPanel";
import type { AskResponse } from "../shared/api/api";

const base: AskResponse = {
	request_id: "req-1",
	question: "how many loans",
	sql: "SELECT COUNT(*) FROM fct_loan_originations",
	explanation: "Counts all loan originations",
	tables_used: ["fct_loan_originations"],
	assumptions: [],
	caveats: ["Includes all statuses"],
	rows: [{ count: 42 }],
	columns: ["count"],
	clarification: null,
};

describe("ResultPanel", () => {
	it("renders clarification message when clarification is set", () => {
		render(
			<ResultPanel
				result={{ ...base, clarification: "Did you mean X or Y?" }}
			/>,
		);
		expect(screen.getByText("Did you mean X or Y?")).toBeInTheDocument();
		expect(screen.queryByText("Counts all loan originations")).toBeNull();
	});

	it("renders explanation text for a normal answer", () => {
		render(<ResultPanel result={base} />);
		expect(
			screen.getByText("Counts all loan originations"),
		).toBeInTheDocument();
	});

	it("renders data table with correct column header and row value", () => {
		render(<ResultPanel result={base} />);
		expect(
			screen.getByRole("columnheader", { name: "count" }),
		).toBeInTheDocument();
		expect(screen.getByRole("cell", { name: "42" })).toBeInTheDocument();
	});

	it("shows caveats section collapsed with correct count", () => {
		render(<ResultPanel result={base} />);
		expect(screen.getByText("Caveats (1)")).toBeInTheDocument();
	});

	it("expands SQL section on click", async () => {
		const user = userEvent.setup();
		render(<ResultPanel result={base} />);
		await user.click(screen.getByText("SQL"));
		expect(
			screen.getByText("SELECT COUNT(*) FROM fct_loan_originations"),
		).toBeVisible();
	});

	it("renders empty table with zero rows without crashing", () => {
		render(<ResultPanel result={{ ...base, rows: [], columns: ["count"] }} />);
		expect(
			screen.getByText("Counts all loan originations"),
		).toBeInTheDocument();
	});
});
