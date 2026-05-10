/**
 * RTK Query slice for the conversational `/intelligence` surface
 * (HUG-179). Pairs with `threadSlice` — RTK Query owns the persisted
 * server state (thread list, full message history) and this file
 * defines a `usePostMessageMutation` whose custom `queryFn` parses
 * the streaming SSE response and dispatches each event into the slice.
 *
 * The SSE custom queryFn bypasses `fetchBaseQuery`, so the session
 * header (`X-Hughes-Session`) is added manually here. On stream close
 * it invalidates the `Thread:{id}` tag so `useGetThreadQuery` refetches
 * the persisted history (the agent ran tools and wrote rows that
 * weren't in the assistant message stream).
 */

import { baseApi } from "../../shared/api/client";
import { SESSION_HEADER, getSessionId } from "../../shared/telemetry/session";
import { USER_HEADER, getUserId } from "../../shared/telemetry/user";
import {
	type ThreadStreamFinal,
	type ThreadStreamStep,
	streamError,
	streamFinal,
	streamStarted,
	streamStep,
	streamThinking,
	streamToken,
} from "./threadSlice";

// ── Wire types (mirror api.types.threads / api.types.threads_api) ─────────

export interface ThreadTraceEntry {
	step: number;
	kind: string;
	label: string;
	tool: string | null;
	at: string;
}

export interface ThreadMessageWire {
	message_id: string;
	thread_id: string;
	parent_message_id: string | null;
	role: "user" | "assistant" | "tool" | "system";
	content: string | null;
	tool_calls: Record<string, unknown>[] | null;
	tool_results: Record<string, unknown>[] | null;
	openui_dsl: string | null;
	mf_query: Record<string, unknown> | null;
	rows: Record<string, unknown>[] | null;
	// HUG-202 Phase 3 — chronological agent narration trace, persisted on
	// the final-answer ToolMessage. Optional so older threads (created
	// before the column existed) don't break the wire type.
	thinking_trace?: ThreadTraceEntry[] | null;
	created_at: string;
}

export interface ThreadSummaryWire {
	thread_id: string;
	title: string | null;
	started_at: string;
	last_active_at: string;
}

export interface CreateThreadResponse {
	thread_id: string;
	title: string | null;
	started_at: string;
}

export interface GetThreadResponse {
	thread_id: string;
	title: string | null;
	started_at: string;
	last_active_at: string;
	messages: ThreadMessageWire[];
}

export interface ListThreadsResponse {
	threads: ThreadSummaryWire[];
}

export interface PostMessageArg {
	threadId: string;
	content: string;
	parentMessageId?: string | null;
}

// ── SSE parser ────────────────────────────────────────────────────────────

interface ParsedSseEvent {
	event: string;
	data: string;
}

interface ParseResult {
	events: ParsedSseEvent[];
	remainder: string;
}

/**
 * Split an SSE buffer on `\n\n` event delimiters. Each block becomes
 * `{event, data}`; partial trailing block is returned in `remainder`.
 * Comment lines (starting with `:`) and unknown fields are dropped —
 * this is the minimal subset of the SSE spec that sse_starlette emits.
 *
 * Exported so tests can exercise edge cases (split across reads, ping
 * lines, malformed blocks) without spinning up a real EventSource.
 */
// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: SSE parser state machine — splitting it further obscures the per-line dispatch.
export function parseSseBuffer(buffer: string): ParseResult {
	const events: ParsedSseEvent[] = [];
	// sse_starlette / starlette emit CRLF line endings (\r\n\r\n between
	// events). The earlier LF-only split silently produced zero events on
	// the live wire, so the entire stream landed in the trailing flush as
	// a single corrupted "final" block — see HUG-201 follow-up.
	const blocks = buffer.split(/\r?\n\r?\n/);
	const remainder = blocks.pop() ?? "";
	for (const block of blocks) {
		if (block.length === 0) continue;
		let eventName = "message";
		const dataLines: string[] = [];
		let isComment = true;
		for (const rawLine of block.split("\n")) {
			const line = rawLine.replace(/\r$/, "");
			if (line === "" || line.startsWith(":")) continue;
			isComment = false;
			const colon = line.indexOf(":");
			if (colon === -1) continue;
			const field = line.slice(0, colon);
			const value = line.slice(colon + 1).replace(/^\s/, "");
			if (field === "event") eventName = value;
			else if (field === "data") dataLines.push(value);
		}
		if (isComment || dataLines.length === 0) continue;
		events.push({ event: eventName, data: dataLines.join("\n") });
	}
	return { events, remainder };
}

// ── RTK Query slice ───────────────────────────────────────────────────────

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		createThread: build.mutation<CreateThreadResponse, { title?: string }>({
			query: (body) => ({
				url: "/threads",
				method: "POST",
				body: body ?? {},
			}),
			invalidatesTags: ["ThreadList"],
		}),

		getThread: build.query<GetThreadResponse, string>({
			query: (threadId) => ({ url: `/threads/${threadId}` }),
			providesTags: (_result, _err, threadId) => [
				{ type: "Thread", id: threadId },
			],
		}),

		listThreads: build.query<ListThreadsResponse, void>({
			query: () => ({ url: "/threads" }),
			providesTags: ["ThreadList"],
		}),

		/**
		 * Stream a user turn through the agent. The SSE response yields
		 * `step` events as the agent thinks, then a single `final` event
		 * carrying the persisted assistant message + OpenUIDslPayload.
		 * Each event is dispatched into `threadSlice`; on close the
		 * thread cache is invalidated so the persisted history refetches.
		 */
		postMessage: build.mutation<void, PostMessageArg>({
			// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: SSE custom queryFn — every branch is a soft-skip path that needs explicit handling.
			queryFn: async ({ threadId, content, parentMessageId }, api) => {
				api.dispatch(streamStarted());
				const baseUrl =
					typeof window !== "undefined"
						? `${window.location.origin}/api`
						: "/api";
				let response: Response;
				try {
					response = await fetch(`${baseUrl}/threads/${threadId}/messages`, {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							[SESSION_HEADER]: getSessionId(),
							[USER_HEADER]: getUserId(),
							Accept: "text/event-stream",
						},
						body: JSON.stringify({
							content,
							parent_message_id: parentMessageId ?? null,
						}),
					});
				} catch (err) {
					const message = err instanceof Error ? err.message : "network error";
					api.dispatch(streamError(message));
					return { error: { status: "FETCH_ERROR" as const, error: message } };
				}
				if (!response.ok || !response.body) {
					const message = `HTTP ${response.status}`;
					api.dispatch(streamError(message));
					return {
						error: { status: response.status, data: message },
					};
				}
				const reader = response.body.getReader();
				const decoder = new TextDecoder();
				let buffer = "";
				try {
					while (true) {
						const { done, value } = await reader.read();
						if (done) break;
						buffer += decoder.decode(value, { stream: true });
						const { events, remainder } = parseSseBuffer(buffer);
						buffer = remainder;
						for (const ev of events) {
							dispatchSseEvent(api.dispatch, ev);
						}
					}
					// Flush any final block that didn't end with \n\n.
					buffer += decoder.decode();
					if (buffer.length > 0) {
						const { events } = parseSseBuffer(`${buffer}\n\n`);
						for (const ev of events) {
							dispatchSseEvent(api.dispatch, ev);
						}
					}
				} catch (err) {
					const message =
						err instanceof Error ? err.message : "stream read error";
					api.dispatch(streamError(message));
					return {
						error: { status: "CUSTOM_ERROR" as const, error: message },
					};
				}
				api.dispatch(
					baseApi.util.invalidateTags([
						{ type: "Thread", id: threadId },
						"ThreadList",
					]),
				);
				return { data: undefined };
			},
		}),
	}),
	overrideExisting: false,
});

function dispatchSseEvent(
	dispatch: (a: { type: string; payload?: unknown }) => unknown,
	ev: ParsedSseEvent,
): void {
	let parsed: unknown;
	try {
		parsed = JSON.parse(ev.data);
	} catch {
		return;
	}
	if (ev.event === "step") {
		dispatch(streamStep(parsed as ThreadStreamStep));
	} else if (ev.event === "thinking") {
		dispatch(streamThinking(parsed as { step: number; line: string }));
	} else if (ev.event === "token") {
		dispatch(streamToken(parsed as { content_delta: string }));
	} else if (ev.event === "final") {
		dispatch(streamFinal(parsed as ThreadStreamFinal));
	}
}

export const {
	useCreateThreadMutation,
	useGetThreadQuery,
	useListThreadsQuery,
	usePostMessageMutation,
} = slice;
