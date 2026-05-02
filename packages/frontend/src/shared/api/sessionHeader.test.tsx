import { renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useGetTrustQuery } from "../../features/trust/api";
import {
	SESSION_HEADER,
	_resetSessionForTesting,
	getSessionId,
} from "../telemetry/session";
import * as api from "./api";
import { createStore } from "./store";

let capturedHeaders: Headers | null = null;
let originalFetch: typeof global.fetch;

beforeEach(() => {
	_resetSessionForTesting();
	capturedHeaders = null;
	// Replace the test setup's bridge fetch with a header-capturing stub
	// just for this file. The bridge resets back via afterEach.
	originalFetch = global.fetch;
	global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
		// Capture headers from either path: legacy fetchJson passes
		// init.headers (a Headers instance), RTK passes a Request.
		if (input instanceof Request) {
			capturedHeaders = input.headers;
		} else {
			capturedHeaders = new Headers(init?.headers);
		}
		return new Response(
			JSON.stringify({
				origence_row_count: 1,
				symitar_row_count: 1,
				reconciliation_match_rate: 1,
				known_caveats: [],
			}),
			{ status: 200, headers: { "Content-Type": "application/json" } },
		);
	}) as unknown as typeof fetch;
});

afterEach(() => {
	global.fetch = originalFetch;
	vi.restoreAllMocks();
});

function Wrapper({ children }: { children: React.ReactNode }) {
	const store = createStore();
	return <ReduxProvider store={store}>{children}</ReduxProvider>;
}

describe("RTK base query — X-Hughes-Session header", () => {
	it("attaches X-Hughes-Session on every RTK Query request", async () => {
		const expectedSid = getSessionId();
		renderHook(() => useGetTrustQuery(), { wrapper: Wrapper });
		await waitFor(() => {
			expect(capturedHeaders).not.toBeNull();
		});
		expect(capturedHeaders?.get(SESSION_HEADER)).toBe(expectedSid);
	});
});

describe("legacy fetchJson — X-Hughes-Session header", () => {
	it("attaches X-Hughes-Session on api.* fetcher calls too", async () => {
		const expectedSid = getSessionId();
		await api.getHistory();
		expect(capturedHeaders?.get(SESSION_HEADER)).toBe(expectedSid);
	});
});
