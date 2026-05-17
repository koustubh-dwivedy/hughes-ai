/**
 * Redux slice for the active conversation surface at /intelligence
 * (HUG-179). Holds the per-tab UI state that doesn't belong in the RTK
 * Query cache — the in-flight SSE step list, the composer's draft
 * text, the streaming flag, and the last terminal payload.
 *
 * The persisted message history comes from `useGetThreadQuery` and is
 * NOT duplicated here; reading messages goes to RTK Query, transient
 * UI state goes to this slice.
 */

import { type PayloadAction, createSlice } from "@reduxjs/toolkit";

/**
 * Mirrors `api.types.threads_api.StreamStep`. The wire kind is
 * `"tool_call" | "tool_result" | "thinking"`; we widen to string so an
 * unexpected value from a future backend doesn't crash the slice.
 */
export interface ThreadStreamStep {
	step: number;
	kind: string;
	name: string | null;
	args: Record<string, unknown> | null;
	result: Record<string, unknown> | null;
}

/**
 * Mirrors `api.types.openui.OpenUIDslPayload`. Re-declared here (rather
 * than imported from a generated client) because the frontend doesn't
 * yet have a typed-API codegen step; the shape is small and stable.
 */
export interface OpenUIDslPayload {
	dsl_text: string;
	validated: boolean;
	validation_errors: { code: string; message: string }[];
	validated_at: string | null;
}

/**
 * Mirrors `api.types.threads_api.StreamFinal`. The persisted message
 * carries the full `ThreadMessage` shape; we only type the slots the UI
 * reads, leaving the rest as `Record<string, unknown>` to avoid drift.
 */
export interface ThreadStreamFinal {
	message: {
		message_id: string;
		thread_id: string;
		role: string;
		content: string | null;
		[key: string]: unknown;
	};
	openui: OpenUIDslPayload | null;
}

export interface PendingQuestion {
	content: string;
	threadId: string | null;
	submittedAt: number;
}

/**
 * Live activity surfaces during a lead-agent turn so the user can see
 * what the agent is currently doing (plan version, in-flight subagents,
 * last tool name). All three fields reset on streamStarted /
 * streamFinal / streamError. Drives the live-activity panel inside
 * ThinkingBubble.
 */
export interface LivePlan {
	plan_id: string;
	version: number;
	step_count: number;
}
export interface LiveSubagent {
	call_id: string;
	prompt: string;
	status: "spawned" | "completed" | "failed";
	error: string | null;
}

export interface ThreadState {
	currentThreadId: string | null;
	draftInput: string;
	streaming: boolean;
	// Which thread the in-flight stream belongs to. Set by streamStarted,
	// cleared by streamFinal / streamError. Lets the UI render the live
	// bubble on its source thread regardless of which thread the user
	// is currently viewing — and avoids the "switch threads mid-stream,
	// everything disappears" bug where setCurrentThread used to wipe
	// streaming state on every view change.
	streamingThreadId: string | null;
	steps: ThreadStreamStep[];
	lastFinal: ThreadStreamFinal | null;
	error: string | null;
	pendingQuestion: PendingQuestion | null;
	// HUG-202 Phase 1 — current Thinking-box line. The box shows ONE
	// line at a time (replaces, not appends) while streaming. Cleared on
	// streamStarted / streamFinal / streamError so a new turn starts
	// from the default copy.
	narrationLine: string | null;
	// HUG-202 Phase 2 — accumulating LLM-streamed answer summary. Grows
	// token-by-token while the agent generates `final_answer.summary`.
	// Cleared at the start of each turn and on streamFinal once the
	// canonical persisted message takes over.
	streamingSummary: string;
	// Live activity (Bug 4, 2026-05-17) — populated from
	// research.plan.drafted, research.subagent.*, and step events so
	// the user can see what the lead is currently doing. Reset on
	// streamStarted/Final/Error.
	livePlan: LivePlan | null;
	liveSubagents: LiveSubagent[];
	liveCurrentTool: string | null;
}

export const initialThreadState: ThreadState = {
	currentThreadId: null,
	draftInput: "",
	streaming: false,
	streamingThreadId: null,
	steps: [],
	lastFinal: null,
	error: null,
	pendingQuestion: null,
	narrationLine: null,
	streamingSummary: "",
	livePlan: null,
	liveSubagents: [],
	liveCurrentTool: null,
};

const slice = createSlice({
	name: "thread",
	initialState: initialThreadState,
	reducers: {
		setCurrentThread(state, action: PayloadAction<string | null>) {
			// Just update which thread the UI is currently viewing.
			// Streaming buffers are tagged with `streamingThreadId` and
			// stay alive across view-switches — the UI gates rendering
			// on equality with `currentThreadId`. Wiping buffers here
			// caused the "switch away mid-stream → everything vanishes"
			// bug, because the SSE was still running for the original
			// thread but the slice no longer knew about it.
			state.currentThreadId = action.payload;
			state.error = null;
		},
		pendingQuestionSubmitted(
			state,
			action: PayloadAction<{ content: string; threadId: string | null }>,
		) {
			state.pendingQuestion = {
				content: action.payload.content,
				threadId: action.payload.threadId,
				submittedAt: Date.now(),
			};
		},
		pendingQuestionCleared(state) {
			state.pendingQuestion = null;
		},
		// Rebind an existing pendingQuestion's threadId. Used right after
		// createThread completes for a submit-from-empty-state flow: the
		// pendingQuestion was dispatched with threadId=null (before the
		// new thread existed); once we know its id, we rebind so the
		// pending is correctly scoped. Without this, clicking "+ New
		// thread" later puts the user back on /intelligence (threadId=null)
		// and the pending (still null-scoped) falsely matches the view,
		// suppressing the starter screen.
		pendingQuestionRebound(state, action: PayloadAction<{ threadId: string }>) {
			if (state.pendingQuestion !== null) {
				state.pendingQuestion.threadId = action.payload.threadId;
			}
		},
		setDraft(state, action: PayloadAction<string>) {
			state.draftInput = action.payload;
		},
		streamStarted(state, action: PayloadAction<{ threadId: string }>) {
			state.streaming = true;
			state.streamingThreadId = action.payload.threadId;
			state.steps = [];
			state.lastFinal = null;
			state.error = null;
			state.narrationLine = null;
			state.streamingSummary = "";
			state.livePlan = null;
			state.liveSubagents = [];
			state.liveCurrentTool = null;
		},
		streamPlanDrafted(state, action: PayloadAction<LivePlan>) {
			state.livePlan = action.payload;
		},
		streamSubagentSpawned(
			state,
			action: PayloadAction<{ call_id: string; prompt: string }>,
		) {
			const { call_id, prompt } = action.payload;
			// Drop any prior entry for this call_id so a re-spawn updates in
			// place rather than duplicating.
			state.liveSubagents = state.liveSubagents.filter(
				(s) => s.call_id !== call_id,
			);
			// Most-recent-first; cap at 10 so a runaway lead doesn't bloat
			// the slice.
			state.liveSubagents.unshift({
				call_id,
				prompt,
				status: "spawned",
				error: null,
			});
			state.liveSubagents = state.liveSubagents.slice(0, 10);
		},
		streamSubagentCompleted(state, action: PayloadAction<{ call_id: string }>) {
			const row = state.liveSubagents.find(
				(s) => s.call_id === action.payload.call_id,
			);
			if (row) row.status = "completed";
		},
		streamSubagentFailed(
			state,
			action: PayloadAction<{ call_id: string; error: string }>,
		) {
			const row = state.liveSubagents.find(
				(s) => s.call_id === action.payload.call_id,
			);
			if (row) {
				row.status = "failed";
				row.error = action.payload.error;
			}
		},
		streamTool(state, action: PayloadAction<{ name: string | null }>) {
			state.liveCurrentTool = action.payload.name;
		},
		streamStep(state, action: PayloadAction<ThreadStreamStep>) {
			state.steps.push(action.payload);
		},
		streamThinking(
			state,
			action: PayloadAction<{ step: number; line: string }>,
		) {
			state.narrationLine = action.payload.line;
		},
		streamToken(state, action: PayloadAction<{ content_delta: string }>) {
			state.streamingSummary += action.payload.content_delta;
		},
		streamFinal(state, action: PayloadAction<ThreadStreamFinal>) {
			state.lastFinal = action.payload;
			state.streaming = false;
			state.streamingThreadId = null;
			state.narrationLine = null;
			state.livePlan = null;
			state.liveSubagents = [];
			state.liveCurrentTool = null;
			// Keep streamingSummary populated briefly so the bubble
			// doesn't flash empty between final-event landing and the
			// persisted-thread refetch arriving. The next streamStarted
			// resets it.
		},
		streamCleared(state) {
			state.steps = [];
			state.lastFinal = null;
			state.error = null;
			state.narrationLine = null;
			state.streamingSummary = "";
		},
		streamError(state, action: PayloadAction<string>) {
			state.error = action.payload;
			state.streaming = false;
			state.streamingThreadId = null;
			state.narrationLine = null;
			state.streamingSummary = "";
			state.livePlan = null;
			state.liveSubagents = [];
			state.liveCurrentTool = null;
		},
	},
});

export const threadSlice = slice;
export const {
	setCurrentThread,
	setDraft,
	streamStarted,
	streamStep,
	streamThinking,
	streamToken,
	streamFinal,
	streamCleared,
	streamError,
	streamPlanDrafted,
	streamSubagentSpawned,
	streamSubagentCompleted,
	streamSubagentFailed,
	streamTool,
	pendingQuestionSubmitted,
	pendingQuestionCleared,
	pendingQuestionRebound,
} = slice.actions;
export default slice.reducer;
