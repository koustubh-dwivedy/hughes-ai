import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it, vi } from "vitest";
import { createStore } from "../../../shared/api/store";
import StepList from "./StepList";
import * as api from "./api";
import type { Step } from "./types";

function _step(
	ordinal: number,
	description: string,
	status: Step["status"],
): Step {
	return {
		step_id: `00000000-0000-0000-0000-00000000000${ordinal}`,
		plan_id: "00000000-0000-0000-0000-0000000000aa",
		ordinal,
		description,
		status,
		assigned_subagent: null,
		started_at: null,
		completed_at: null,
	};
}

function renderWithSteps(steps: Step[]) {
	vi.spyOn(api, "useGetResearchStepsQuery").mockReturnValue({
		data: { steps },
		isLoading: false,
		isFetching: false,
		isSuccess: true,
		isError: false,
		// biome-ignore lint/suspicious/noExplicitAny: minimal RTK Query mock
	} as any);
	const store = createStore();
	return render(
		<ReduxProvider store={store}>
			<StepList
				threadId="00000000-0000-0000-0000-0000000000bb"
				planId="00000000-0000-0000-0000-0000000000aa"
			/>
		</ReduxProvider>,
	);
}

describe("StepList", () => {
	it("renders nothing when no steps", () => {
		const { container } = renderWithSteps([]);
		expect(container.firstChild).toBeNull();
	});

	it("renders each step in ordinal order with status chip", () => {
		renderWithSteps([
			_step(2, "Compare A and B", "pending"),
			_step(1, "Pull metric A", "complete"),
		]);
		const rows = screen.getAllByText(/Pull metric A|Compare A and B/);
		// Sorted ascending by ordinal.
		expect(rows[0]).toHaveTextContent("Pull metric A");
		expect(rows[1]).toHaveTextContent("Compare A and B");
	});

	it("renders correct status chips for parallel running steps", () => {
		renderWithSteps([
			_step(1, "step a", "running"),
			_step(2, "step b", "running"),
			_step(3, "step c", "pending"),
		]);
		// Two running chips visible simultaneously (parallel execution).
		const runningChips = screen.getAllByTestId("status-running");
		expect(runningChips).toHaveLength(2);
	});

	it("renders failed status correctly", () => {
		renderWithSteps([_step(1, "broken step", "failed")]);
		expect(screen.getByTestId("status-failed")).toBeInTheDocument();
	});
});
