/**
 * SSE-event dispatcher unit tests. After the per-thread slice refactor
 * each helper takes the threadId and forwards it through to the slice
 * action payload.
 */

import { describe, expect, it, vi } from "vitest";
import { dispatchLivePlan, dispatchSubagentEvent } from "./researchSseDispatch";
import { streamPlanDrafted, streamSubagentSpawned } from "./threadSlice";

const TID = "t1";

describe("researchSseDispatch — live plan badge", () => {
	it("reads step_count from plan_json.steps (the wire shape plan_tool emits)", () => {
		const dispatch = vi.fn();
		dispatchLivePlan(dispatch, TID, {
			plan_id: "p1",
			version: 1,
			plan_json: { steps: [{}, {}, {}, {}] },
		});
		expect(dispatch).toHaveBeenCalledWith(
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p1", version: 1, step_count: 4 },
			}),
		);
	});

	it("falls back to plan_json.plan when present (older snapshot shape)", () => {
		const dispatch = vi.fn();
		dispatchLivePlan(dispatch, TID, {
			plan_id: "p2",
			version: 2,
			plan_json: { plan: [{}, {}] },
		});
		expect(dispatch).toHaveBeenCalledWith(
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p2", version: 2, step_count: 2 },
			}),
		);
	});

	it("renders step_count = 0 when neither key is present (graceful default)", () => {
		const dispatch = vi.fn();
		dispatchLivePlan(dispatch, TID, {
			plan_id: "p3",
			version: 1,
			plan_json: {},
		});
		expect(dispatch).toHaveBeenCalledWith(
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p3", version: 1, step_count: 0 },
			}),
		);
	});
});

describe("researchSseDispatch — subagent events", () => {
	it("dispatches streamSubagentSpawned with threadId + call_id + prompt", () => {
		const dispatch = vi.fn();
		dispatchSubagentEvent(dispatch, TID, "research.subagent.spawned", {
			call_id: "c1",
			prompt: "fetch metric X",
		});
		expect(dispatch).toHaveBeenCalledWith(
			streamSubagentSpawned({
				threadId: TID,
				call_id: "c1",
				prompt: "fetch metric X",
			}),
		);
	});

	it("noop on unknown event names", () => {
		const dispatch = vi.fn();
		dispatchSubagentEvent(dispatch, TID, "research.subagent.unknown", {
			call_id: "c1",
		});
		expect(dispatch).not.toHaveBeenCalled();
	});
});
