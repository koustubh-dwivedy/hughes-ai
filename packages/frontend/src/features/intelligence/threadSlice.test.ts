import { describe, expect, it } from "vitest";
import reducer, {
	initialThreadState,
	setCurrentThread,
	setDraft,
	streamCleared,
	streamError,
	streamFinal,
	streamStarted,
	streamStep,
	streamThinking,
	type ThreadState,
	type ThreadStreamFinal,
	type ThreadStreamStep,
} from "./threadSlice";

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
		thread_id: "t1",
		role: "tool",
		content: '{"summary":"hi"}',
	},
	openui: {
		dsl_text: 'root = Stack(["hi"])',
		validated: true,
		validation_errors: [],
		validated_at: "2026-05-06T00:00:00Z",
	},
};

describe("threadSlice", () => {
	it("returns the initial state when no action matches", () => {
		const state = reducer(undefined, { type: "noop" });
		expect(state).toEqual(initialThreadState);
	});

	it("setCurrentThread from one thread to another preserves in-flight streaming state", () => {
		// Pre-fix this reducer wiped the streaming buffers, which broke
		// the "submit on A → click B → click A back → see live progress"
		// flow because the SSE was still alive but the slice forgot.
		// Now buffers belong to whichever thread `streamingThreadId`
		// points at; setCurrentThread only updates the view target.
		const dirty: ThreadState = {
			currentThreadId: "t-old",
			draftInput: "hello",
			streaming: true,
			streamingThreadId: "t-old",
			steps: [sampleStep],
			lastFinal: sampleFinal,
			error: "boom",
			pendingQuestion: {
				content: "Q",
				threadId: "t-old",
				submittedAt: 1,
			},
			narrationLine: "Looking up…",
			streamingSummary: "partial answer ",
			livePlan: null,
			liveSubagents: [],
			liveCurrentTool: null,
		};
		const next = reducer(dirty, setCurrentThread("t-new"));
		expect(next.currentThreadId).toBe("t-new");
		// Streaming buffers must survive — they belong to t-old.
		expect(next.streaming).toBe(true);
		expect(next.streamingThreadId).toBe("t-old");
		expect(next.steps).toEqual([sampleStep]);
		expect(next.lastFinal).toEqual(sampleFinal);
		expect(next.pendingQuestion?.content).toBe("Q");
		expect(next.narrationLine).toBe("Looking up…");
		expect(next.streamingSummary).toBe("partial answer ");
		// `error` is genuinely transient; it's fine to drop on view switch.
		expect(next.error).toBeNull();
		expect(next.draftInput).toBe("hello");
	});

	it("setCurrentThread from empty (null) to a freshly-created thread preserves in-flight state", () => {
		// HUG-201 follow-up: when the user submits from /intelligence,
		// createThread + navigate fires `setCurrentThread(<newId>)`. We
		// must NOT wipe the optimistic pending bubble or the streaming
		// flag — they belong to the just-submitted turn.
		const inFlight: ThreadState = {
			currentThreadId: null,
			draftInput: "",
			streaming: true,
			streamingThreadId: null,
			steps: [sampleStep],
			lastFinal: null,
			error: null,
			pendingQuestion: {
				content: "What's our LTD ratio?",
				threadId: null,
				submittedAt: 1,
			},
			narrationLine: null,
			streamingSummary: "",
			livePlan: null,
			liveSubagents: [],
			liveCurrentTool: null,
		};
		const next = reducer(inFlight, setCurrentThread("t-new"));
		expect(next.currentThreadId).toBe("t-new");
		expect(next.streaming).toBe(true);
		expect(next.pendingQuestion?.content).toBe("What's our LTD ratio?");
		expect(next.steps).toEqual([sampleStep]);
	});

	it("setCurrentThread(null) clears the id while still resetting buffers", () => {
		const next = reducer(
			{ ...initialThreadState, currentThreadId: "t1" },
			setCurrentThread(null),
		);
		expect(next.currentThreadId).toBeNull();
	});

	it("setDraft updates the composer text without touching anything else", () => {
		const next = reducer(initialThreadState, setDraft("what's our LTD ratio?"));
		expect(next.draftInput).toBe("what's our LTD ratio?");
		expect(next.steps).toEqual([]);
		expect(next.streaming).toBe(false);
	});

	it("streamStarted flips the flag, tags the thread, and clears prior buffers", () => {
		const dirty: ThreadState = {
			...initialThreadState,
			steps: [sampleStep],
			lastFinal: sampleFinal,
			error: "stale",
		};
		const next = reducer(dirty, streamStarted({ threadId: "t-active" }));
		expect(next.streaming).toBe(true);
		expect(next.streamingThreadId).toBe("t-active");
		expect(next.steps).toEqual([]);
		expect(next.lastFinal).toBeNull();
		expect(next.error).toBeNull();
	});

	it("streamStep appends to the steps list in arrival order", () => {
		const a = reducer(initialThreadState, streamStep(sampleStep));
		const b = reducer(
			a,
			streamStep({
				step: 2,
				kind: "tool_result",
				name: "list_metrics",
				args: null,
				result: { ok: true },
			}),
		);
		expect(b.steps).toHaveLength(2);
		expect(b.steps[0].step).toBe(1);
		expect(b.steps[1].step).toBe(2);
	});

	it("streamFinal stores the terminal payload, ends streaming, untags the thread", () => {
		const mid: ThreadState = {
			...initialThreadState,
			streaming: true,
			streamingThreadId: "t-active",
		};
		const next = reducer(mid, streamFinal(sampleFinal));
		expect(next.lastFinal).toEqual(sampleFinal);
		expect(next.streaming).toBe(false);
		expect(next.streamingThreadId).toBeNull();
	});

	it("streamCleared resets buffers but keeps thread id and draft", () => {
		const dirty: ThreadState = {
			currentThreadId: "t1",
			draftInput: "in flight",
			streaming: false,
			streamingThreadId: null,
			steps: [sampleStep],
			lastFinal: sampleFinal,
			error: "x",
			pendingQuestion: null,
			narrationLine: null,
			streamingSummary: "",
			livePlan: null,
			liveSubagents: [],
			liveCurrentTool: null,
		};
		const next = reducer(dirty, streamCleared());
		expect(next.steps).toEqual([]);
		expect(next.lastFinal).toBeNull();
		expect(next.error).toBeNull();
		expect(next.currentThreadId).toBe("t1");
		expect(next.draftInput).toBe("in flight");
	});

	it("streamError records the message, stops streaming, untags the thread", () => {
		const mid: ThreadState = {
			...initialThreadState,
			streaming: true,
			streamingThreadId: "t-active",
		};
		const next = reducer(mid, streamError("network down"));
		expect(next.error).toBe("network down");
		expect(next.streaming).toBe(false);
		expect(next.streamingThreadId).toBeNull();
	});

	it("streamThinking replaces narrationLine in place (rolling display)", () => {
		// HUG-202 Phase 1: each event REPLACES the previous narration so
		// the Thinking box stays at one line. No history is kept here —
		// the persistent trace lives elsewhere.
		const start: ThreadState = { ...initialThreadState, streaming: true };
		const after1 = reducer(
			start,
			streamThinking({ step: 1, line: "Looking up available metrics…" }),
		);
		expect(after1.narrationLine).toBe("Looking up available metrics…");
		const after2 = reducer(
			after1,
			streamThinking({ step: 2, line: "Found 24 metrics" }),
		);
		expect(after2.narrationLine).toBe("Found 24 metrics");
	});

	it("streamFinal clears narrationLine so the Thinking bubble unmounts cleanly", () => {
		const mid: ThreadState = {
			...initialThreadState,
			streaming: true,
			narrationLine: "Working…",
		};
		const next = reducer(mid, streamFinal(sampleFinal));
		expect(next.narrationLine).toBeNull();
		expect(next.streaming).toBe(false);
	});

	it("streamStarted resets narrationLine for a new turn", () => {
		const mid: ThreadState = {
			...initialThreadState,
			narrationLine: "carry-over from previous turn",
		};
		const next = reducer(mid, streamStarted({ threadId: "t1" }));
		expect(next.narrationLine).toBeNull();
		expect(next.streaming).toBe(true);
		expect(next.streamingThreadId).toBe("t1");
	});
});
