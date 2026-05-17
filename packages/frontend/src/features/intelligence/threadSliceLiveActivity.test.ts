/**
 * Live-activity reducer tests (Bug 4 + Issue 2 per-thread refactor).
 *
 * After the per-thread slice refactor, every stream reducer takes a
 * threadId payload and writes into `streams[threadId]`. This file
 * locks the live-activity reducers (plan, subagent, current tool) and
 * the lifecycle clears on streamStarted / streamFinal / streamError.
 */

import { describe, expect, it } from "vitest";
import reducer, {
	initialThreadState,
	pendingQuestionRebound,
	pendingQuestionSubmitted,
	streamError,
	streamFinal,
	streamPlanDrafted,
	streamStarted,
	streamSubagentCompleted,
	streamSubagentFailed,
	streamSubagentSpawned,
	streamTool,
	type ThreadStreamFinal,
} from "./threadSlice";

const TID = "t1";

const sampleFinal: ThreadStreamFinal = {
	message: { message_id: "m1", thread_id: TID, role: "tool", content: "{}" },
	openui: null,
};

function streamingStart() {
	return reducer(initialThreadState, streamStarted({ threadId: TID }));
}

describe("threadSlice — live activity (Bug 4 + Issue 2 per-thread)", () => {
	it("streamPlanDrafted populates livePlan with version + step_count", () => {
		const next = reducer(
			streamingStart(),
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p1", version: 2, step_count: 4 },
			}),
		);
		expect(next.streams[TID].livePlan).toEqual({
			plan_id: "p1",
			version: 2,
			step_count: 4,
		});
	});

	it("streamSubagentSpawned prepends most-recent-first; cap at 10", () => {
		let state = streamingStart();
		for (let i = 0; i < 12; i++) {
			state = reducer(
				state,
				streamSubagentSpawned({
					threadId: TID,
					call_id: `c${i}`,
					prompt: `q${i}`,
				}),
			);
		}
		const subs = state.streams[TID].liveSubagents;
		expect(subs).toHaveLength(10);
		expect(subs[0].call_id).toBe("c11");
		expect(subs[9].call_id).toBe("c2");
	});

	it("streamSubagentCompleted flips status on the matching row", () => {
		let s = streamingStart();
		s = reducer(
			s,
			streamSubagentSpawned({ threadId: TID, call_id: "c1", prompt: "X" }),
		);
		s = reducer(s, streamSubagentCompleted({ threadId: TID, call_id: "c1" }));
		expect(s.streams[TID].liveSubagents[0].status).toBe("completed");
	});

	it("streamSubagentFailed flips status + records error", () => {
		let s = streamingStart();
		s = reducer(
			s,
			streamSubagentSpawned({ threadId: TID, call_id: "c1", prompt: "X" }),
		);
		s = reducer(
			s,
			streamSubagentFailed({
				threadId: TID,
				call_id: "c1",
				error: "metric not found",
			}),
		);
		expect(s.streams[TID].liveSubagents[0].status).toBe("failed");
		expect(s.streams[TID].liveSubagents[0].error).toBe("metric not found");
	});

	it("streamTool stores the last tool name for the activity panel", () => {
		const next = reducer(
			streamingStart(),
			streamTool({ threadId: TID, name: "run_subagent" }),
		);
		expect(next.streams[TID].liveCurrentTool).toBe("run_subagent");
	});

	it("streamStarted resets the thread's live-activity fields", () => {
		let s = streamingStart();
		s = reducer(
			s,
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p", version: 1, step_count: 2 },
			}),
		);
		s = reducer(
			s,
			streamSubagentSpawned({ threadId: TID, call_id: "c", prompt: "p" }),
		);
		s = reducer(s, streamTool({ threadId: TID, name: "stale" }));
		// New stream on the SAME thread = fresh slot.
		const next = reducer(s, streamStarted({ threadId: TID }));
		expect(next.streams[TID].livePlan).toBeNull();
		expect(next.streams[TID].liveSubagents).toEqual([]);
		expect(next.streams[TID].liveCurrentTool).toBeNull();
	});

	it("streamFinal clears live activity but keeps lastFinal", () => {
		let s = streamingStart();
		s = reducer(
			s,
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p", version: 1, step_count: 2 },
			}),
		);
		s = reducer(
			s,
			streamSubagentSpawned({ threadId: TID, call_id: "c", prompt: "p" }),
		);
		s = reducer(s, streamTool({ threadId: TID, name: "mf_query" }));
		const next = reducer(s, streamFinal({ threadId: TID, final: sampleFinal }));
		expect(next.streams[TID].livePlan).toBeNull();
		expect(next.streams[TID].liveSubagents).toEqual([]);
		expect(next.streams[TID].liveCurrentTool).toBeNull();
		expect(next.streams[TID].lastFinal).toEqual(sampleFinal);
		expect(next.streamingThreadIds).not.toContain(TID);
	});

	it("streamError clears live activity + records error", () => {
		let s = streamingStart();
		s = reducer(
			s,
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p", version: 1, step_count: 2 },
			}),
		);
		const next = reducer(s, streamError({ threadId: TID, error: "boom" }));
		expect(next.streams[TID].livePlan).toBeNull();
		expect(next.streams[TID].error).toBe("boom");
		expect(next.streamingThreadIds).not.toContain(TID);
	});
});

describe("threadSlice — pendingQuestionRebound (the '+ New thread' fix)", () => {
	it("rebinds an existing pendingQuestion's threadId in place", () => {
		const a = reducer(
			initialThreadState,
			pendingQuestionSubmitted({ content: "Q1", threadId: null }),
		);
		expect(a.pendingQuestion?.threadId).toBeNull();
		const b = reducer(a, pendingQuestionRebound({ threadId: "newId" }));
		expect(b.pendingQuestion?.threadId).toBe("newId");
		expect(b.pendingQuestion?.content).toBe("Q1");
		expect(b.pendingQuestion?.submittedAt).toBe(a.pendingQuestion?.submittedAt);
	});

	it("is a safe no-op when there is no pendingQuestion to rebind", () => {
		const next = reducer(
			initialThreadState,
			pendingQuestionRebound({ threadId: "newId" }),
		);
		expect(next.pendingQuestion).toBeNull();
	});
});
