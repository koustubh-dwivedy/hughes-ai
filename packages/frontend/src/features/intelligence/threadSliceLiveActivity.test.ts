/**
 * Bug 4 (2026-05-17): live-activity reducer tests, split out of
 * threadSlice.test.ts so the original file stays under the 300-line
 * structural cap.
 *
 * Covers the new reducers (streamPlanDrafted, streamSubagentSpawned,
 * streamSubagentCompleted, streamSubagentFailed, streamTool) and the
 * lifecycle-clear behaviour on streamStarted / streamFinal / streamError.
 */

import { describe, expect, it } from "vitest";
import reducer, {
	initialThreadState,
	streamError,
	streamFinal,
	streamPlanDrafted,
	streamStarted,
	streamSubagentCompleted,
	streamSubagentFailed,
	streamSubagentSpawned,
	streamTool,
	type ThreadState,
	type ThreadStreamFinal,
} from "./threadSlice";

const sampleFinal: ThreadStreamFinal = {
	message: { message_id: "m1", thread_id: "t1", role: "tool", content: "{}" },
	openui: null,
};

describe("threadSlice — live activity (Bug 4)", () => {
	it("streamPlanDrafted populates livePlan with version + step_count", () => {
		const next = reducer(
			{ ...initialThreadState, streaming: true },
			streamPlanDrafted({ plan_id: "p1", version: 2, step_count: 4 }),
		);
		expect(next.livePlan).toEqual({ plan_id: "p1", version: 2, step_count: 4 });
	});

	it("streamSubagentSpawned prepends a row most-recent-first; cap at 10", () => {
		let state = { ...initialThreadState, streaming: true };
		for (let i = 0; i < 12; i++) {
			state = reducer(
				state,
				streamSubagentSpawned({ call_id: `c${i}`, prompt: `q${i}` }),
			);
		}
		expect(state.liveSubagents).toHaveLength(10);
		expect(state.liveSubagents[0].call_id).toBe("c11");
		expect(state.liveSubagents[9].call_id).toBe("c2");
	});

	it("streamSubagentCompleted flips status on the matching row", () => {
		const a = reducer(
			{ ...initialThreadState, streaming: true },
			streamSubagentSpawned({ call_id: "c1", prompt: "fetch X" }),
		);
		const b = reducer(a, streamSubagentCompleted({ call_id: "c1" }));
		expect(b.liveSubagents[0].status).toBe("completed");
	});

	it("streamSubagentFailed flips status + records error", () => {
		const a = reducer(
			{ ...initialThreadState, streaming: true },
			streamSubagentSpawned({ call_id: "c1", prompt: "fetch X" }),
		);
		const b = reducer(
			a,
			streamSubagentFailed({ call_id: "c1", error: "metric not found" }),
		);
		expect(b.liveSubagents[0].status).toBe("failed");
		expect(b.liveSubagents[0].error).toBe("metric not found");
	});

	it("streamTool stores the last tool name for the activity panel", () => {
		const next = reducer(
			{ ...initialThreadState, streaming: true },
			streamTool({ name: "run_subagent" }),
		);
		expect(next.liveCurrentTool).toBe("run_subagent");
	});

	it("streamStarted resets all live-activity fields for a new turn", () => {
		const mid: ThreadState = {
			...initialThreadState,
			livePlan: { plan_id: "p", version: 1, step_count: 2 },
			liveSubagents: [
				{ call_id: "c1", prompt: "p", status: "completed", error: null },
			],
			liveCurrentTool: "stale",
		};
		const next = reducer(mid, streamStarted({ threadId: "t1" }));
		expect(next.livePlan).toBeNull();
		expect(next.liveSubagents).toEqual([]);
		expect(next.liveCurrentTool).toBeNull();
	});

	it("streamFinal clears all live-activity fields when the turn ends", () => {
		const mid: ThreadState = {
			...initialThreadState,
			streaming: true,
			livePlan: { plan_id: "p", version: 1, step_count: 2 },
			liveSubagents: [
				{ call_id: "c1", prompt: "p", status: "spawned", error: null },
			],
			liveCurrentTool: "mf_query",
		};
		const next = reducer(mid, streamFinal(sampleFinal));
		expect(next.livePlan).toBeNull();
		expect(next.liveSubagents).toEqual([]);
		expect(next.liveCurrentTool).toBeNull();
	});

	it("streamError clears all live-activity fields", () => {
		const mid: ThreadState = {
			...initialThreadState,
			streaming: true,
			livePlan: { plan_id: "p", version: 1, step_count: 2 },
			liveSubagents: [
				{ call_id: "c1", prompt: "p", status: "spawned", error: null },
			],
			liveCurrentTool: "mf_query",
		};
		const next = reducer(mid, streamError("boom"));
		expect(next.livePlan).toBeNull();
		expect(next.liveSubagents).toEqual([]);
		expect(next.liveCurrentTool).toBeNull();
	});
});
