import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AskResponse } from "../../../shared/api/api";
import * as telemetry from "../../../shared/telemetry/client";
import ResultRenderer, { classifyResult } from "./ResultRenderer";

function withProviders(ui: React.ReactNode) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

const BASE: AskResponse = {
	request_id: "req-1",
	question: "Q",
	sql: null,
	explanation: null,
	tables_used: [],
	assumptions: [],
	caveats: [],
	rows: [],
	columns: [],
	clarification: null,
};

afterEach(() => {
	vi.restoreAllMocks();
});

describe("classifyResult", () => {
	it("classifies a non-null clarification as clarification", () => {
		expect(
			classifyResult({ ...BASE, clarification: "Did you mean foo?" }),
		).toBe("clarification");
	});

	it("classifies single numeric cell as number", () => {
		expect(
			classifyResult({
				...BASE,
				columns: ["count"],
				rows: [{ count: 42 }],
			}),
		).toBe("number");
	});

	it("classifies date+numeric series with multiple rows as chart", () => {
		expect(
			classifyResult({
				...BASE,
				columns: ["month", "value"],
				rows: [
					{ month: "2025-01", value: 1 },
					{ month: "2025-02", value: 2 },
				],
			}),
		).toBe("chart");
	});

	it("classifies multi-row non-time-series as table", () => {
		expect(
			classifyResult({
				...BASE,
				columns: ["officer", "amount"],
				rows: [
					{ officer: "A", amount: 100 },
					{ officer: "B", amount: 200 },
				],
			}),
		).toBe("table");
	});

	it("falls back to table for empty rows without clarification", () => {
		expect(classifyResult({ ...BASE, columns: ["x"], rows: [] })).toBe("table");
	});
});

describe("ResultRenderer — rendering branches", () => {
	it("renders clarification branch with role=note", () => {
		withProviders(
			<ResultRenderer result={{ ...BASE, clarification: "Which branch?" }} />,
		);
		expect(screen.getByRole("note")).toHaveTextContent("Which branch?");
	});

	it("renders single big number for number branch", () => {
		withProviders(
			<ResultRenderer
				result={{
					...BASE,
					columns: ["loan_count"],
					rows: [{ loan_count: 1234 }],
					explanation: "Total active loans.",
				}}
			/>,
		);
		expect(screen.getByLabelText("Result value")).toHaveTextContent("1,234");
		expect(screen.getByText("Total active loans.")).toBeInTheDocument();
	});

	it("renders chart branch with view-as-table toggle", () => {
		withProviders(
			<ResultRenderer
				result={{
					...BASE,
					columns: ["month", "balance"],
					rows: [
						{ month: "2025-01", balance: 100 },
						{ month: "2025-02", balance: 110 },
					],
				}}
			/>,
		);
		const toggle = screen.getByRole("button", { name: "View as table" });
		expect(toggle).toBeInTheDocument();
		fireEvent.click(toggle);
		expect(
			screen.getByRole("button", { name: "View as chart" }),
		).toBeInTheDocument();
		expect(screen.getByRole("table")).toBeInTheDocument();
	});

	it("renders DataTable for plain table results", () => {
		withProviders(
			<ResultRenderer
				result={{
					...BASE,
					columns: ["officer", "amount"],
					rows: [
						{ officer: "A", amount: 100 },
						{ officer: "B", amount: 200 },
					],
				}}
			/>,
		);
		expect(screen.getByRole("table")).toBeInTheDocument();
	});
});

describe("ResultRenderer — telemetry", () => {
	it("emits chat.result.rendered with the classified type", () => {
		const spy = vi.spyOn(telemetry, "emit");
		withProviders(
			<ResultRenderer
				result={{
					...BASE,
					request_id: "req-42",
					columns: ["count"],
					rows: [{ count: 7 }],
				}}
			/>,
		);
		expect(spy).toHaveBeenCalledWith({
			type: "chat.result.rendered",
			query_id: "req-42",
			row_count: 1,
			result_type: "number",
		});
	});

	it("emits chart type for time-series", () => {
		const spy = vi.spyOn(telemetry, "emit");
		withProviders(
			<ResultRenderer
				result={{
					...BASE,
					request_id: "req-9",
					columns: ["month", "value"],
					rows: [
						{ month: "2025-01", value: 1 },
						{ month: "2025-02", value: 2 },
					],
				}}
			/>,
		);
		expect(spy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "chat.result.rendered",
				query_id: "req-9",
				row_count: 2,
				result_type: "chart",
			}),
		);
	});
});
