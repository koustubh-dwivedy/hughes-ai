/**
 * Deterministic SSE response helper for Playwright (HUG-179).
 *
 * Builds the byte stream that sse_starlette.EventSourceResponse emits
 * so `page.route("**\/threads/:id/messages", ...)` can return an
 * agent-like stream without spinning up the real backend. Each event
 * is `event: <name>\ndata: <json>\n\n`. Comment lines (`:`) can be
 * interleaved to mimic keep-alive pings.
 */

export interface SseEvent {
	event: "step" | "final";
	data: Record<string, unknown>;
}

/**
 * Format a list of events as a single SSE body string.
 *
 * Note: `\n\n` is the SSE record terminator. We append it *after* every
 * record (including the last) so the frontend's parser flushes the
 * final event without relying on the EOF-flush fallback path.
 */
export function formatSse(events: SseEvent[]): string {
	return events
		.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
		.join("");
}

/**
 * Build a `final_answer` terminal event with sensible defaults. Pass
 * `openui_dsl` to control what `<OpenUIRenderer>` renders; pass
 * `summary` to set the assistant's prose answer.
 */
export function buildFinalEvent(opts: {
	threadId: string;
	messageId?: string;
	summary: string;
	openuiDsl?: string;
	mfQuery?: Record<string, unknown>;
	rows?: Record<string, unknown>[];
}): SseEvent {
	const dsl = opts.openuiDsl ?? null;
	const content = JSON.stringify({
		summary: opts.summary,
		openui_dsl: dsl,
		mf_query: opts.mfQuery ?? null,
		rows: opts.rows ?? null,
	});
	return {
		event: "final",
		data: {
			message: {
				message_id: opts.messageId ?? `m-${opts.threadId}-${Date.now()}`,
				thread_id: opts.threadId,
				parent_message_id: null,
				role: "tool",
				content,
				tool_calls: null,
				tool_results: [{ name: "final_answer" }],
				openui_dsl: dsl,
				mf_query: opts.mfQuery ?? null,
				rows: opts.rows ?? null,
				created_at: new Date().toISOString(),
			},
			openui:
				dsl === null
					? null
					: {
							dsl_text: dsl,
							validated: true,
							validation_errors: [],
							validated_at: new Date().toISOString(),
						},
		},
	};
}

/**
 * Build a sequence of plausible `step` events to precede a final.
 * Mirrors what the real agent emits: list_metrics → mf_query →
 * thinking → final.
 */
export function defaultStepLeadIn(): SseEvent[] {
	return [
		{
			event: "step",
			data: {
				step: 1,
				kind: "tool_call",
				name: "list_metrics",
				args: {},
				result: null,
			},
		},
		{
			event: "step",
			data: {
				step: 2,
				kind: "tool_result",
				name: "list_metrics",
				args: null,
				result: {},
			},
		},
		{
			event: "step",
			data: {
				step: 3,
				kind: "tool_call",
				name: "mf_query",
				args: {},
				result: null,
			},
		},
		{
			event: "step",
			data: {
				step: 4,
				kind: "tool_result",
				name: "mf_query",
				args: null,
				result: { rows: [] },
			},
		},
	];
}
