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
import { SESSION_HEADER } from "../../shared/telemetry/session";
import { createStore } from "../../shared/api/store";
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
			"event: step\r\nid: 1\r\ndata: {\"step\":1}\r\nfoo: bar\r\n\n",
		);
		expect(events).toEqual([{ event: "step", data: '{"step":1}' }]);
	});

	it("supports two events fed across separate calls (state in caller buffer)", () => {
		const first = parseSseBuffer('event: step\ndata: {"step":1}\n\nevent: f');
		const second = parseSseBuffer(`${first.remainder}inal\ndata: {"x":1}\n\n`);
		expect(first.events).toHaveLength(1);
		expect(second.events).toEqual([{ event: "final", data: '{"x":1}' }]);
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
		expect(state.streaming).toBe(false);
		expect(state.steps).toHaveLength(2);
		expect(state.steps[0].name).toBe("list_metrics");
		expect(state.lastFinal?.message.message_id).toBe("m1");

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
			expect(store.getState().thread.error).toContain("HTTP 500");
			expect(store.getState().thread.streaming).toBe(false);
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

		expect(store.getState().thread.error).toBe("offline");
		expect(store.getState().thread.streaming).toBe(false);
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
		expect(store.getState().thread.lastFinal?.message.message_id).toBe("m9");
	});
});
