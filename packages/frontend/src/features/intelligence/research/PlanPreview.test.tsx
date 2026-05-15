import { fireEvent, render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it } from "vitest";
import { createStore } from "../../../shared/api/store";
import PlanPreview from "./PlanPreview";
import type { Plan } from "./types";

const FIXTURE_PLAN: Plan = {
	plan_id: "00000000-0000-0000-0000-000000000001",
	thread_id: "00000000-0000-0000-0000-000000000002",
	version: 1,
	status: "draft",
	created_at: "2026-05-15T00:00:00Z",
	plan_json: {
		route: "deep",
		reason: "multi-step decomposition needed",
		research_question_summary: "Drivers of YoY past-due delta",
		plan: [
			{
				ordinal: 1,
				description: "Pull past-due exposure for latest month",
				dependencies: [],
			},
			{
				ordinal: 2,
				description: "Pull past-due exposure for same month one year ago",
				dependencies: [],
			},
			{
				ordinal: 3,
				description: "Compute YoY deltas by branch",
				dependencies: [1, 2],
			},
		],
	},
};

function renderPlan(plan: Plan) {
	const store = createStore();
	return render(
		<ReduxProvider store={store}>
			<PlanPreview plan={plan} />
		</ReduxProvider>,
	);
}

describe("PlanPreview", () => {
	it("renders the plan title + reason", () => {
		renderPlan(FIXTURE_PLAN);
		expect(screen.getByText(/Drivers of YoY past-due delta/)).toBeInTheDocument();
		expect(
			screen.getByText(/multi-step decomposition needed/),
		).toBeInTheDocument();
	});

	it("renders each step in ordinal order", () => {
		renderPlan(FIXTURE_PLAN);
		const items = screen.getAllByRole("listitem");
		expect(items).toHaveLength(3);
		expect(items[0]).toHaveTextContent("Pull past-due exposure for latest month");
		expect(items[2]).toHaveTextContent(/depends on steps 1, 2/);
	});

	it("exposes Approve + Cancel buttons", () => {
		renderPlan(FIXTURE_PLAN);
		expect(screen.getByRole("button", { name: /Approve/ })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Cancel/ })).toBeInTheDocument();
	});

	it("Approve button is enabled by default", () => {
		renderPlan(FIXTURE_PLAN);
		const approve = screen.getByRole("button", { name: /Approve/ });
		expect(approve).toBeEnabled();
		// Smoke: clicking doesn't crash. The mutation hook handles the
		// actual network call; we don't assert on it here (covered by
		// the api.ts tag-invalidation logic + backend route tests).
		fireEvent.click(approve);
	});
});
