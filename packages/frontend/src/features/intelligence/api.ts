/** RTK Query slice for /intelligence (HUG-179). Pairs with threadSlice
 * — postMessage's queryFn parses SSE and dispatches per event. */
import { baseApi, baseUrl } from "../../shared/api/client";
import { SESSION_HEADER, getSessionId } from "../../shared/telemetry/session";
import { USER_HEADER, getUserId } from "../../shared/telemetry/user";
import {
	RESEARCH_PLAN_EVENTS,
	RESEARCH_SUBAGENT_EVENTS,
	dispatchLivePlan,
	dispatchResearchPlanInvalidation,
	dispatchSubagentEvent,
} from "./researchSseDispatch";
import {
	type ThreadStreamFinal,
	type ThreadStreamStep,
	streamError,
	streamFinal,
	streamStarted,
	streamStep,
	streamThinking,
	streamToken,
	streamTool,
} from "./threadSlice";

// HUG-265: synthetic ThreadStreamFinal for close-without-final fallback.
const _SYN_FINAL = (threadId: string): ThreadStreamFinal => ({
	message: {
		message_id: "",
		thread_id: threadId,
		role: "assistant",
		content: null,
	},
	openui: null,
});

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
	// HUG-202: narration trace on final-answer; optional for legacy threads.
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

/** Split an SSE buffer on `\n\n` event delimiters. Exported for tests. */
// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: SSE parser state machine — splitting it further obscures the per-line dispatch.
export function parseSseBuffer(buffer: string): ParseResult {
	const events: ParsedSseEvent[] = [];
	// sse_starlette emits CRLF; LF-only split previously corrupted the wire.
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

		/** Stream a user turn via SSE — dispatches per-event into
		 * `threadSlice`; on close, invalidate thread cache to refetch. */
		postMessage: build.mutation<void, PostMessageArg>({
			// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: SSE custom queryFn — every branch is a soft-skip path that needs explicit handling.
			queryFn: async ({ threadId, content, parentMessageId }, api) => {
				api.dispatch(streamStarted({ threadId }));
				// HUG-260: shared baseUrl → api.tryhughes.com in prod.
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
					api.dispatch(streamError({ threadId, error: message }));
					return { error: { status: "FETCH_ERROR" as const, error: message } };
				}
				if (!response.ok || !response.body) {
					const message = `HTTP ${response.status}`;
					api.dispatch(streamError({ threadId, error: message }));
					return {
						error: { status: response.status, data: message },
					};
				}
				const reader = response.body.getReader();
				const decoder = new TextDecoder();
				let buffer = "";
				// HUG-265: fallback when stream closes without final/error.
				let sawTerminalEvent = false;
				const dispatchAndTrack = (ev: ParsedSseEvent): void => {
					if (ev.event === "final" || ev.event === "error") {
						sawTerminalEvent = true;
					}
					dispatchSseEvent(api.dispatch, threadId, ev);
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
					// Flush any final block that didn't end with \n\n.
					buffer += decoder.decode();
					if (buffer.length > 0) {
						const { events } = parseSseBuffer(`${buffer}\n\n`);
						for (const ev of events) {
							dispatchAndTrack(ev);
						}
					}
					if (!sawTerminalEvent) {
						// HUG-265: synthesize streamFinal so UI unlocks.
						api.dispatch(
							streamFinal({ threadId, final: _SYN_FINAL(threadId) }),
						);
					}
				} catch (err) {
					const message =
						err instanceof Error ? err.message : "stream read error";
					api.dispatch(streamError({ threadId, error: message }));
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
				// Real-time title arrives via the SSE `title` event
				// handled in dispatchSseEvent; no setTimeout fallback.
				return { data: undefined };
			},
		}),
	}),
	overrideExisting: false,
});

// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: SSE event-name dispatch — each branch is one tagged event with bespoke payload typing; routing this through a Map would obscure the contract.
function dispatchSseEvent(
	dispatch: (a: { type: string; payload?: unknown }) => unknown,
	threadId: string,
	ev: ParsedSseEvent,
): void {
	let parsed: unknown;
	try {
		parsed = JSON.parse(ev.data);
	} catch {
		return;
	}
	if (ev.event === "step") {
		const step = parsed as ThreadStreamStep;
		dispatch(streamStep({ threadId, step }));
		if (step.kind === "tool_call" && step.name) {
			dispatch(streamTool({ threadId, name: step.name }));
		}
	} else if (ev.event === "thinking") {
		const p = parsed as { step: number; line: string };
		dispatch(streamThinking({ threadId, step: p.step, line: p.line }));
	} else if (ev.event === "token") {
		const p = parsed as { content_delta: string };
		dispatch(streamToken({ threadId, content_delta: p.content_delta }));
	} else if (ev.event === "final") {
		dispatch(streamFinal({ threadId, final: parsed as ThreadStreamFinal }));
	} else if (ev.event === "title") {
		const t = parsed as { thread_id: string; title: string };
		dispatch(
			baseApi.util.invalidateTags([
				"ThreadList",
				{ type: "Thread", id: t.thread_id },
			]) as unknown as { type: string; payload?: unknown },
		);
	} else if (RESEARCH_SUBAGENT_EVENTS.has(ev.event)) {
		dispatchSubagentEvent(dispatch, threadId, ev.event, parsed);
	} else if (RESEARCH_PLAN_EVENTS.has(ev.event)) {
		if (ev.event === "research.plan.drafted")
			dispatchLivePlan(dispatch, threadId, parsed);
		dispatchResearchPlanInvalidation(dispatch, parsed);
	}
}

export const {
	useCreateThreadMutation,
	useGetThreadQuery,
	useListThreadsQuery,
	usePostMessageMutation,
} = slice;
