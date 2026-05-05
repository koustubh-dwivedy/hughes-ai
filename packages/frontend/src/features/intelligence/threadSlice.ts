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

export interface ThreadState {
	currentThreadId: string | null;
	draftInput: string;
	streaming: boolean;
	steps: ThreadStreamStep[];
	lastFinal: ThreadStreamFinal | null;
	error: string | null;
}

export const initialThreadState: ThreadState = {
	currentThreadId: null,
	draftInput: "",
	streaming: false,
	steps: [],
	lastFinal: null,
	error: null,
};

const slice = createSlice({
	name: "thread",
	initialState: initialThreadState,
	reducers: {
		setCurrentThread(state, action: PayloadAction<string | null>) {
			state.currentThreadId = action.payload;
			// New thread context — drop anything still buffered from a
			// previous turn so stale steps don't bleed into the new view.
			state.steps = [];
			state.lastFinal = null;
			state.error = null;
			state.streaming = false;
		},
		setDraft(state, action: PayloadAction<string>) {
			state.draftInput = action.payload;
		},
		streamStarted(state) {
			state.streaming = true;
			state.steps = [];
			state.lastFinal = null;
			state.error = null;
		},
		streamStep(state, action: PayloadAction<ThreadStreamStep>) {
			state.steps.push(action.payload);
		},
		streamFinal(state, action: PayloadAction<ThreadStreamFinal>) {
			state.lastFinal = action.payload;
			state.streaming = false;
		},
		streamCleared(state) {
			state.steps = [];
			state.lastFinal = null;
			state.error = null;
		},
		streamError(state, action: PayloadAction<string>) {
			state.error = action.payload;
			state.streaming = false;
		},
	},
});

export const threadSlice = slice;
export const {
	setCurrentThread,
	setDraft,
	streamStarted,
	streamStep,
	streamFinal,
	streamCleared,
	streamError,
} = slice.actions;
export default slice.reducer;
