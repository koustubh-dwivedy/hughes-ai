import { describe, expect, it } from "vitest";
import {
	selectCurrentStream,
	selectIsStreamingOn,
	selectStreamFor,
} from "./threadSelectors";
import reducer, {
	EMPTY_STREAM,
	initialThreadState,
	setCurrentThread,
	setDraft,
	streamCleared,
	streamError,
	streamFinal,
	streamStarted,
	streamStep,
	streamThinking,
	type ThreadStreamFinal,
	type ThreadStreamStep,
} from "./threadSlice";

const T1 = "t1";
const T2 = "t2";

const sampleStep: ThreadStreamStep = {
	step: 1,
	kind: "tool_call",
	name: "list_metrics",
	args: {},
	result: null,
};

const sampleFinal: ThreadStreamFinal = {
	message: {
		message_id: "m1",
		thread_id: T1,
		role: "tool",
		content: '{"summary":"hi"}',
	},
	openui: null,
};

describe("threadSlice — per-thread streaming state", () => {
	it("returns the initial state when no action matches", () => {
		const state = reducer(undefined, { type: "noop" });
		expect(state).toEqual(initialThreadState);
		expect(state.streamingThreadIds).toEqual([]);
		expect(state.streams).toEqual({});
	});

	it("streamStarted creates a per-thread slot and registers the thread", () => {
		const next = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		expect(next.streamingThreadIds).toEqual([T1]);
		expect(next.streams[T1]).toBeDefined();
		expect(next.streams[T1].narrationLine).toBeNull();
		expect(next.streams[T1].steps).toEqual([]);
	});

	it("two concurrent streams DO NOT clobber each other (the Issue 2 fix)", () => {
		// Repro: thread A starts streaming, then user clicks "+ New thread"
		// and submits on thread B. Pre-fix, streamStarted on B would wipe
		// A's narrationLine / livePlan / liveSubagents because the slice
		// held one global slot. Now each thread owns its own slot.
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(
			s,
			streamThinking({ threadId: T1, step: 1, line: "A thinking" }),
		);
		s = reducer(s, streamStep({ threadId: T1, step: sampleStep }));
		// Second stream starts on T2.
		s = reducer(s, streamStarted({ threadId: T2 }));
		// T1's slot must still hold A's progress.
		expect(s.streams[T1].narrationLine).toBe("A thinking");
		expect(s.streams[T1].steps).toEqual([sampleStep]);
		// T2 has a fresh slot.
		expect(s.streams[T2].narrationLine).toBeNull();
		// Both threads are registered as streaming.
		expect([...s.streamingThreadIds].sort()).toEqual([T1, T2].sort());
	});

	it("streamStep appends to the matching thread's slot only", () => {
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(s, streamStarted({ threadId: T2 }));
		s = reducer(s, streamStep({ threadId: T1, step: sampleStep }));
		expect(s.streams[T1].steps).toEqual([sampleStep]);
		expect(s.streams[T2].steps).toEqual([]);
	});

	it("streamThinking writes to the right thread", () => {
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(s, streamStarted({ threadId: T2 }));
		s = reducer(s, streamThinking({ threadId: T1, step: 1, line: "A" }));
		s = reducer(s, streamThinking({ threadId: T2, step: 1, line: "B" }));
		expect(s.streams[T1].narrationLine).toBe("A");
		expect(s.streams[T2].narrationLine).toBe("B");
	});

	it("streamFinal preserves lastFinal + streamingSummary and unregisters the thread", () => {
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(s, streamStarted({ threadId: T2 }));
		s = reducer(s, streamFinal({ threadId: T1, final: sampleFinal }));
		expect(s.streams[T1].lastFinal).toEqual(sampleFinal);
		expect(s.streams[T1].narrationLine).toBeNull();
		expect(s.streamingThreadIds).toEqual([T2]);
	});

	it("streamError stores the error and unregisters the thread", () => {
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(s, streamError({ threadId: T1, error: "network down" }));
		expect(s.streams[T1].error).toBe("network down");
		expect(s.streamingThreadIds).toEqual([]);
	});

	it("streamCleared resets the matching thread's slot only", () => {
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(s, streamThinking({ threadId: T1, step: 1, line: "x" }));
		s = reducer(s, streamCleared({ threadId: T1 }));
		expect(s.streams[T1].narrationLine).toBeNull();
		expect(s.streams[T1].steps).toEqual([]);
	});
});

describe("threadSlice — setCurrentThread + draft (orthogonal to streaming)", () => {
	it("setCurrentThread switches the view target without touching streams", () => {
		let s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		s = reducer(s, streamThinking({ threadId: T1, step: 1, line: "A" }));
		s = reducer(s, setCurrentThread(T2));
		expect(s.currentThreadId).toBe(T2);
		// T1's stream survives the view switch.
		expect(s.streams[T1].narrationLine).toBe("A");
		expect(s.streamingThreadIds).toEqual([T1]);
	});

	it("setDraft only updates draftInput", () => {
		const next = reducer(initialThreadState, setDraft("hello"));
		expect(next.draftInput).toBe("hello");
		expect(next.streams).toEqual({});
	});
});

describe("threadSlice — selectors", () => {
	function rootWith(slice: ReturnType<typeof reducer>) {
		return { thread: slice };
	}

	it("selectCurrentStream returns the slot for currentThreadId", () => {
		let s = reducer(initialThreadState, setCurrentThread(T1));
		s = reducer(s, streamStarted({ threadId: T1 }));
		s = reducer(s, streamThinking({ threadId: T1, step: 1, line: "live" }));
		expect(selectCurrentStream(rootWith(s)).narrationLine).toBe("live");
	});

	it("selectCurrentStream returns EMPTY_STREAM when there is no current thread", () => {
		const s = reducer(initialThreadState, setCurrentThread(null));
		expect(selectCurrentStream(rootWith(s))).toBe(EMPTY_STREAM);
	});

	it("selectStreamFor returns EMPTY_STREAM for a thread we've never streamed on", () => {
		expect(selectStreamFor(rootWith(initialThreadState), "missing")).toBe(
			EMPTY_STREAM,
		);
	});

	it("selectIsStreamingOn returns true only for registered thread ids", () => {
		const s = reducer(initialThreadState, streamStarted({ threadId: T1 }));
		expect(selectIsStreamingOn(rootWith(s), T1)).toBe(true);
		expect(selectIsStreamingOn(rootWith(s), T2)).toBe(false);
		expect(selectIsStreamingOn(rootWith(s), null)).toBe(false);
	});
});
