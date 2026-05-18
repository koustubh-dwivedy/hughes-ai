/** HUG-266: shared SSE consumer used by both `postMessage` (the
 * submit path) and `tailTurn` (the reload-reconnect path). Reads the
 * Response body, parses SSE events, dispatches them, and falls back
 * to a synthetic streamFinal if the stream closes without a terminal
 * event (HUG-265 contract). */
import { baseApi } from "../../shared/api/client";
import { parseSseBuffer } from "./api";
import {
	type ThreadStreamFinal,
	streamError,
	streamFinal,
} from "./threadSlice";

interface ParsedSseEvent {
	event: string;
	data: string;
}

type Dispatch = (a: { type: string; payload?: unknown }) => unknown;

const _SYN_FINAL = (threadId: string): ThreadStreamFinal => ({
	message: {
		message_id: "",
		thread_id: threadId,
		role: "assistant",
		content: null,
	},
	openui: null,
});

// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: SSE consumer state machine — every branch is a soft-skip path that needs explicit handling, matching the pre-extraction shape in postMessage's queryFn.
export async function consumeSseStream(
	response: Response,
	threadId: string,
	dispatch: Dispatch,
	dispatchSseEvent: (
		dispatch: Dispatch,
		threadId: string,
		ev: ParsedSseEvent,
	) => void,
): Promise<{ ok: true } | { ok: false; error: string }> {
	if (!response.body) {
		const message = `HTTP ${response.status}: no body`;
		dispatch(streamError({ threadId, error: message }));
		return { ok: false, error: message };
	}
	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	let sawTerminalEvent = false;
	const dispatchAndTrack = (ev: ParsedSseEvent): void => {
		if (ev.event === "final" || ev.event === "error") {
			sawTerminalEvent = true;
		}
		dispatchSseEvent(dispatch, threadId, ev);
	};
	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });
			const { events, remainder } = parseSseBuffer(buffer);
			buffer = remainder;
			for (const ev of events) {
				dispatchAndTrack(ev);
			}
		}
		buffer += decoder.decode();
		if (buffer.length > 0) {
			const { events } = parseSseBuffer(`${buffer}\n\n`);
			for (const ev of events) {
				dispatchAndTrack(ev);
			}
		}
		if (!sawTerminalEvent) {
			dispatch(streamFinal({ threadId, final: _SYN_FINAL(threadId) }));
		}
	} catch (err) {
		const message = err instanceof Error ? err.message : "stream read error";
		dispatch(streamError({ threadId, error: message }));
		return { ok: false, error: message };
	}
	dispatch(
		baseApi.util.invalidateTags([
			{ type: "Thread", id: threadId },
			"ThreadList",
		]),
	);
	return { ok: true };
}
