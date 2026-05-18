/**
 * Unit tests for the /intelligence RTK Query slice (HUG-179).
 *
 * Mocks `fetch` directly because the SSE custom queryFn bypasses
 * `fetchBaseQuery`. `ReadableStream` from a Uint8Array array is the
 * cleanest way to feed deterministic chunks to the consumer; jsdom
 * (vitest's default env) ships with a working ReadableStream.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createStore } from "../../shared/api/store";
import { SESSION_HEADER } from "../../shared/telemetry/session";
import { parseSseBuffer, usePostMessageMutation } from "./api";

afterEach(() => {
	vi.restoreAllMocks();
});

function withStore(store: ReturnType<typeof createStore>) {
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <ReduxProvider store={store}>{children}</ReduxProvider>;
	};
}

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
	const encoder = new TextEncoder();
	let i = 0;
	return new ReadableStream<Uint8Array>({
		pull(controller) {
			if (i < chunks.length) {
				controller.enqueue(encoder.encode(chunks[i]));
				i += 1;
			} else {
				controller.close();
			}
		},
	});
}

function sseResponse(chunks: string[], status = 200): Response {
	return new Response(makeStream(chunks), {
		status,
		headers: { "Content-Type": "text/event-stream" },
	});
}

describe("parseSseBuffer", () => {
	it("parses a single complete event", () => {
		const { events, remainder } = parseSseBuffer(
			'event: step\ndata: {"step":1}\n\n',
		);
		expect(events).toEqual([{ event: "step", data: '{"step":1}' }]);
		expect(remainder).toBe("");
	});

	it("retains a partial trailing block in the remainder", () => {
		const { events, remainder } = parseSseBuffer(
			'event: step\ndata: {"step":1}\n\nevent: final\ndata: {"par',
		);
		expect(events).toHaveLength(1);
		expect(remainder).toBe('event: final\ndata: {"par');
	});

	it("ignores comment (`:`) keep-alive lines", () => {
		const { events } = parseSseBuffer(
			': ping - 2026-05-06\n\nevent: step\ndata: {"step":1}\n\n',
		);
		expect(events).toEqual([{ event: "step", data: '{"step":1}' }]);
	});

	it("returns no events when the buffer is purely whitespace + comments", () => {
		const { events } = parseSseBuffer(": ping\n\n: ping again\n\n");
		expect(events).toEqual([]);
	});

	it("survives blocks with unknown fields and trailing CR characters", () => {
		const { events } = parseSseBuffer(
			'event: step\r\nid: 1\r\ndata: {"step":1}\r\nfoo: bar\r\n\n',
		);
		expect(events).toEqual([{ event: "step", data: '{"step":1}' }]);
	});

	it("supports two events fed across separate calls (state in caller buffer)", () => {
		const first = parseSseBuffer('event: step\ndata: {"step":1}\n\nevent: f');
		const second = parseSseBuffer(`${first.remainder}inal\ndata: {"x":1}\n\n`);
		expect(first.events).toHaveLength(1);
		expect(second.events).toEqual([{ event: "final", data: '{"x":1}' }]);
	});

	it("parses CRLF-separated wire output (sse_starlette default)", () => {
		// Regression: the live wire emits \r\n between fields and \r\n\r\n
		// between events. Splitting on \n\n alone produced zero events on
		// this transport, leading to the streaming flag never clearing.
		const { events, remainder } = parseSseBuffer(
			'event: step\r\ndata: {"step":1}\r\n\r\nevent: final\r\ndata: {"ok":true}\r\n\r\n',
		);
		expect(events).toEqual([
			{ event: "step", data: '{"step":1}' },
			{ event: "final", data: '{"ok":true}' },
		]);
		expect(remainder).toBe("");
	});
});

describe("usePostMessageMutation — SSE wiring", () => {
	it("dispatches streamStarted, streamStep, streamFinal and invalidates Thread tag", async () => {
		const fetchSpy = vi
			.spyOn(global, "fetch")
			.mockResolvedValue(
				sseResponse([
					'event: step\ndata: {"step":1,"kind":"tool_call","name":"list_metrics","args":{},"result":null}\n\n',
					'event: step\ndata: {"step":2,"kind":"tool_result","name":"list_metrics","args":null,"result":{}}\n\n',
					'event: final\ndata: {"message":{"message_id":"m1","thread_id":"t1","role":"tool","content":"{}"},"openui":null}\n\n',
				]),
			);
		const store = createStore();
		const wrapper = withStore(store);
		const { result } = renderHook(() => usePostMessageMutation(), { wrapper });
		await act(async () => {
			await result.current[0]({ threadId: "t1", content: "hello" }).unwrap();
		});

		const state = store.getState().thread;
		// After streamFinal the thread is removed from streamingThreadIds
		// but its slot (steps, lastFinal) persists.
		expect(state.streamingThreadIds).not.toContain("t1");
		expect(state.streams.t1.steps).toHaveLength(2);
		expect(state.streams.t1.steps[0].name).toBe("list_metrics");
		expect(state.streams.t1.lastFinal?.message.message_id).toBe("m1");

		// Verify session header was attached.
		expect(fetchSpy).toHaveBeenCalledTimes(1);
		const init = fetchSpy.mock.calls[0][1] as RequestInit;
		const headers = init.headers as Record<string, string>;
		expect(headers[SESSION_HEADER]).toBeDefined();
		expect(headers["Content-Type"]).toBe("application/json");
		expect(headers.Accept).toBe("text/event-stream");
	});

	it("dispatches streamError on HTTP error and resolves the mutation as a failure", async () => {
		vi.spyOn(global, "fetch").mockResolvedValue(
			new Response("oops", { status: 500 }),
		);
		const store = createStore();
		const wrapper = withStore(store);
		const { result } = renderHook(() => usePostMessageMutation(), { wrapper });
		await act(async () => {
			const r = await result.current[0]({ threadId: "t1", content: "hi" });
			expect("error" in r).toBe(true);
		});

		await waitFor(() => {
			expect(store.getState().thread.streams.t1?.error).toContain("HTTP 500");
			expect(store.getState().thread.streamingThreadIds).not.toContain("t1");
		});
	});

	it("dispatches streamError when fetch throws (network failure)", async () => {
		vi.spyOn(global, "fetch").mockRejectedValue(new Error("offline"));
		const store = createStore();
		const wrapper = withStore(store);
		const { result } = renderHook(() => usePostMessageMutation(), { wrapper });
		await act(async () => {
			const r = await result.current[0]({ threadId: "t1", content: "hi" });
			expect("error" in r).toBe(true);
		});

		expect(store.getState().thread.streams.t1?.error).toBe("offline");
		expect(store.getState().thread.streamingThreadIds).not.toContain("t1");
	});

	it("flushes a final block that did not end with \\n\\n", async () => {
		// The agent-side ProducingTask occasionally closes the stream
		// without a trailing blank line; the queryFn must still surface
		// the last event.
		vi.spyOn(global, "fetch").mockResolvedValue(
			sseResponse([
				'event: final\ndata: {"message":{"message_id":"m9","thread_id":"t1","role":"tool","content":"{}"},"openui":null}',
			]),
		);
		const store = createStore();
		const wrapper = withStore(store);
		const { result } = renderHook(() => usePostMessageMutation(), { wrapper });
		await act(async () => {
			await result.current[0]({ threadId: "t1", content: "x" }).unwrap();
		});
		expect(
			store.getState().thread.streams.t1?.lastFinal?.message.message_id,
		).toBe("m9");
	});

	// HUG-265 — regression test for the "Hello" lock-up bug.
	it("synthesizes streamFinal when SSE closes without event:final", async () => {
		// Pre-fix server behaviour: lead LLM replies with prose + no
		// tool_calls; graph._route returns END; chat_process_message
		// emits thinking+step but no event:final. Without the fallback,
		// streamingThreadIds keeps "t1" and the composer stays locked.
		vi.spyOn(global, "fetch").mockResolvedValue(
			sseResponse([
				"event: stream.start\ndata: {}\n\n",
				'event: thinking\ndata: {"step":1,"line":"Reasoning…"}\n\n',
				'event: step\ndata: {"step":1,"kind":"thinking","name":null,"args":null,"result":null}\n\n',
			]),
		);
		const store = createStore();
		const wrapper = withStore(store);
		const { result } = renderHook(() => usePostMessageMutation(), { wrapper });
		await act(async () => {
			await result.current[0]({ threadId: "t1", content: "Hello" }).unwrap();
		});

		const state = store.getState().thread;
		// The load-bearing assertion: composer must unlock.
		expect(state.streamingThreadIds).not.toContain("t1");
		// Synthetic streamFinal also clears live-activity slots.
		expect(state.streams.t1.narrationLine).toBeNull();
		expect(state.streams.t1.livePlan).toBeNull();
		// The synthetic payload sets a placeholder lastFinal with the
		// expected thread_id and a sentinel empty message_id so callers
		// can distinguish it from a real final if they need to.
		expect(state.streams.t1.lastFinal?.message.message_id).toBe("");
		expect(state.streams.t1.lastFinal?.message.thread_id).toBe("t1");
		// error must NOT be set — the stream closed normally, just incomplete.
		expect(state.streams.t1.error).toBeNull();
	});

	it("does NOT synthesize when event:final arrives — real payload preserved", async () => {
		vi.spyOn(global, "fetch").mockResolvedValue(
			sseResponse([
				'event: final\ndata: {"message":{"message_id":"m1","thread_id":"t1","role":"tool","content":"{}"},"openui":null}\n\n',
			]),
		);
		const store = createStore();
		const wrapper = withStore(store);
		const { result } = renderHook(() => usePostMessageMutation(), { wrapper });
		await act(async () => {
			await result.current[0]({
				threadId: "t1",
				content: "real query",
			}).unwrap();
		});
		const state = store.getState().thread;
		expect(state.streamingThreadIds).not.toContain("t1");
		// Real final's message_id, not the synthetic placeholder.
		expect(state.streams.t1.lastFinal?.message.message_id).toBe("m1");
	});
});
