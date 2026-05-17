/**
 * Selectors for the per-thread streaming state in `threadSlice`.
 *
 * Extracted from `threadSlice.ts` to keep that file under the 300-line
 * structural cap. Consumers should prefer these helpers over reaching
 * into the slice shape directly so the contract stays stable as the
 * slice shape evolves.
 */

import {
	EMPTY_STREAM,
	type PerThreadStream,
	type ThreadState,
} from "./threadSlice";

type RootLike = { thread: ThreadState };

export function selectStreamFor(
	state: RootLike,
	threadId: string | null,
): PerThreadStream {
	if (threadId === null) return EMPTY_STREAM;
	return state.thread.streams[threadId] ?? EMPTY_STREAM;
}

export function selectCurrentStream(state: RootLike): PerThreadStream {
	return selectStreamFor(state, state.thread.currentThreadId);
}

export function selectIsStreamingOn(
	state: RootLike,
	threadId: string | null,
): boolean {
	if (threadId === null) return false;
	return state.thread.streamingThreadIds.includes(threadId);
}

export function selectIsStreamingOnCurrentThread(state: RootLike): boolean {
	return selectIsStreamingOn(state, state.thread.currentThreadId);
}

export function selectAnyStreamActive(state: RootLike): boolean {
	return state.thread.streamingThreadIds.length > 0;
}
