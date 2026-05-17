/**
 * Redux slice for the active conversation surface at /intelligence.
 * Streaming state is keyed by threadId so multiple threads can stream
 * concurrently without clobbering each other. Each thread gets a
 * `PerThreadStream` slot in `streams[threadId]`; the set of threads
 * with an active SSE stream lives in `streamingThreadIds`. Selectors
 * live in `./threadSelectors`.
 */
import { type PayloadAction, createSlice } from "@reduxjs/toolkit";

// Wire types — mirror api.types.threads_api / api.types.openui.
export interface ThreadStreamStep {
	step: number;
	kind: string;
	name: string | null;
	args: Record<string, unknown> | null;
	result: Record<string, unknown> | null;
}
export interface OpenUIDslPayload {
	dsl_text: string;
	validated: boolean;
	validation_errors: { code: string; message: string }[];
	validated_at: string | null;
}
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

/** Per-thread streaming state slot. */
export interface PerThreadStream {
	narrationLine: string | null;
	streamingSummary: string;
	livePlan: LivePlan | null;
	liveSubagents: LiveSubagent[];
	liveCurrentTool: string | null;
	steps: ThreadStreamStep[];
	lastFinal: ThreadStreamFinal | null;
	error: string | null;
}

function freshStream(): PerThreadStream {
	return {
		narrationLine: null,
		streamingSummary: "",
		livePlan: null,
		liveSubagents: [],
		liveCurrentTool: null,
		steps: [],
		lastFinal: null,
		error: null,
	};
}
export const EMPTY_STREAM: PerThreadStream = freshStream();

export interface ThreadState {
	currentThreadId: string | null;
	draftInput: string;
	pendingQuestion: PendingQuestion | null;
	/** ThreadIds with an SSE stream currently in flight. */
	streamingThreadIds: string[];
	/** Per-thread streaming state (narration, plan, subagents, ...). */
	streams: Record<string, PerThreadStream>;
}

export const initialThreadState: ThreadState = {
	currentThreadId: null,
	draftInput: "",
	pendingQuestion: null,
	streamingThreadIds: [],
	streams: {},
};

function ensureSlot(state: ThreadState, threadId: string): void {
	if (!state.streams[threadId]) {
		state.streams[threadId] = freshStream();
	}
}

const slice = createSlice({
	name: "thread",
	initialState: initialThreadState,
	reducers: {
		setCurrentThread(state, action: PayloadAction<string | null>) {
			// Streaming slots persist across view switches; the UI reads
			// the slot for `currentThreadId` so each thread shows its own
			// progress when the user navigates to it.
			state.currentThreadId = action.payload;
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
		pendingQuestionRebound(state, action: PayloadAction<{ threadId: string }>) {
			if (state.pendingQuestion !== null) {
				state.pendingQuestion.threadId = action.payload.threadId;
			}
		},
		setDraft(state, action: PayloadAction<string>) {
			state.draftInput = action.payload;
		},
		streamStarted(state, action: PayloadAction<{ threadId: string }>) {
			const id = action.payload.threadId;
			state.streams[id] = freshStream();
			if (!state.streamingThreadIds.includes(id)) {
				state.streamingThreadIds.push(id);
			}
		},
		streamPlanDrafted(
			state,
			action: PayloadAction<{ threadId: string; plan: LivePlan }>,
		) {
			ensureSlot(state, action.payload.threadId);
			state.streams[action.payload.threadId].livePlan = action.payload.plan;
		},
		streamSubagentSpawned(
			state,
			action: PayloadAction<{
				threadId: string;
				call_id: string;
				prompt: string;
			}>,
		) {
			const { threadId, call_id, prompt } = action.payload;
			ensureSlot(state, threadId);
			const slot = state.streams[threadId];
			slot.liveSubagents = slot.liveSubagents.filter(
				(s) => s.call_id !== call_id,
			);
			slot.liveSubagents.unshift({
				call_id,
				prompt,
				status: "spawned",
				error: null,
			});
			slot.liveSubagents = slot.liveSubagents.slice(0, 10);
		},
		streamSubagentCompleted(
			state,
			action: PayloadAction<{ threadId: string; call_id: string }>,
		) {
			const slot = state.streams[action.payload.threadId];
			if (!slot) return;
			const row = slot.liveSubagents.find(
				(s) => s.call_id === action.payload.call_id,
			);
			if (row) row.status = "completed";
		},
		streamSubagentFailed(
			state,
			action: PayloadAction<{
				threadId: string;
				call_id: string;
				error: string;
			}>,
		) {
			const slot = state.streams[action.payload.threadId];
			if (!slot) return;
			const row = slot.liveSubagents.find(
				(s) => s.call_id === action.payload.call_id,
			);
			if (row) {
				row.status = "failed";
				row.error = action.payload.error;
			}
		},
		streamTool(
			state,
			action: PayloadAction<{ threadId: string; name: string | null }>,
		) {
			ensureSlot(state, action.payload.threadId);
			state.streams[action.payload.threadId].liveCurrentTool =
				action.payload.name;
		},
		streamStep(
			state,
			action: PayloadAction<{ threadId: string; step: ThreadStreamStep }>,
		) {
			ensureSlot(state, action.payload.threadId);
			state.streams[action.payload.threadId].steps.push(action.payload.step);
		},
		streamThinking(
			state,
			action: PayloadAction<{
				threadId: string;
				step: number;
				line: string;
			}>,
		) {
			ensureSlot(state, action.payload.threadId);
			state.streams[action.payload.threadId].narrationLine =
				action.payload.line;
		},
		streamToken(
			state,
			action: PayloadAction<{ threadId: string; content_delta: string }>,
		) {
			ensureSlot(state, action.payload.threadId);
			state.streams[action.payload.threadId].streamingSummary +=
				action.payload.content_delta;
		},
		streamFinal(
			state,
			action: PayloadAction<{ threadId: string; final: ThreadStreamFinal }>,
		) {
			const { threadId, final } = action.payload;
			ensureSlot(state, threadId);
			const slot = state.streams[threadId];
			slot.lastFinal = final;
			slot.narrationLine = null;
			slot.livePlan = null;
			slot.liveSubagents = [];
			slot.liveCurrentTool = null;
			// streamingSummary is intentionally kept so the bubble doesn't
			// flash empty between the final event and the refetch.
			state.streamingThreadIds = state.streamingThreadIds.filter(
				(id) => id !== threadId,
			);
		},
		streamCleared(state, action: PayloadAction<{ threadId: string }>) {
			if (state.streams[action.payload.threadId]) {
				state.streams[action.payload.threadId] = freshStream();
			}
		},
		streamError(
			state,
			action: PayloadAction<{ threadId: string; error: string }>,
		) {
			const { threadId, error } = action.payload;
			ensureSlot(state, threadId);
			const slot = state.streams[threadId];
			slot.error = error;
			slot.narrationLine = null;
			slot.streamingSummary = "";
			slot.livePlan = null;
			slot.liveSubagents = [];
			slot.liveCurrentTool = null;
			state.streamingThreadIds = state.streamingThreadIds.filter(
				(id) => id !== threadId,
			);
		},
	},
});

// Selectors live in `./threadSelectors`.
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
