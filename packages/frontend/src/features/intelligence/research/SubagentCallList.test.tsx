/**
 * SubagentCallList tests — Issue 3 (per-worker mf_query expander).
 * Validates that each subagent row gets its own "Show MetricFlow
 * query" toggle that reveals the worker's mf_query_json block.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it, vi } from "vitest";
import { createStore } from "../../../shared/api/store";
import SubagentCallList from "./SubagentCallList";
import * as api from "./api";
import type { SubagentCall } from "./types";

function _call(
	id: string,
	overrides: Partial<SubagentCall> = {},
): SubagentCall {
	return {
		call_id: id,
		thread_id: "00000000-0000-0000-0000-000000000000",
		plan_id: "00000000-0000-0000-0000-0000000000aa",
		plan_step_ordinal: 1,
		prompt: "fetch metric X",
		status: "complete",
		summary_text: "all good",
		rows_json: null,
		mf_query_json: { metric: "X", group_by: ["branch"] },
		error_text: null,
		started_at: "2026-05-17T00:00:00Z",
		completed_at: "2026-05-17T00:01:00Z",
		...overrides,
	};
}

function renderWithCalls(calls: SubagentCall[]) {
	vi.spyOn(api, "useGetResearchSubagentCallsQuery").mockReturnValue({
		data: { calls },
		isLoading: false,
		isFetching: false,
		isSuccess: true,
		isError: false,
		// biome-ignore lint/suspicious/noExplicitAny: minimal RTK Query mock
	} as any);
	const store = createStore();
	return render(
		<ReduxProvider store={store}>
			<SubagentCallList threadId="t1" planId="p1" />
		</ReduxProvider>,
	);
}

describe("SubagentCallList — per-worker mf_query expander (Issue 3)", () => {
	it("renders one toggle per call when mf_query_json is present", () => {
		renderWithCalls([_call("c1"), _call("c2"), _call("c3")]);
		const toggles = screen.getAllByTestId("subagent-mfquery-toggle");
		expect(toggles).toHaveLength(3);
	});

	it("does NOT render a toggle for a call with no mf_query_json", () => {
		renderWithCalls([
			_call("c1", { mf_query_json: null }),
			_call("c2"),
		]);
		const toggles = screen.getAllByTestId("subagent-mfquery-toggle");
		expect(toggles).toHaveLength(1);
	});

	it("clicking the toggle reveals the JSON block (independently per row)", () => {
		renderWithCalls([_call("c1"), _call("c2")]);
		// Initially nothing expanded.
		expect(screen.queryAllByTestId("subagent-mfquery-block")).toHaveLength(0);
		// Click the first toggle — only that block shows.
		fireEvent.click(screen.getAllByTestId("subagent-mfquery-toggle")[0]);
		expect(screen.getAllByTestId("subagent-mfquery-block")).toHaveLength(1);
	});

	it("renders the section + chip + prompt text for each row", () => {
		renderWithCalls([_call("c1", { prompt: "Q1" }), _call("c2", { prompt: "Q2" })]);
		expect(screen.getByTestId("audit-subagent-calls")).toBeInTheDocument();
		expect(screen.getByText("Q1")).toBeInTheDocument();
		expect(screen.getByText("Q2")).toBeInTheDocument();
	});

	it("renders nothing when there are zero calls", () => {
		const { container } = renderWithCalls([]);
		expect(container).toBeEmptyDOMElement();
	});
});
