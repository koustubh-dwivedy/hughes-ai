import {
	type Mock,
	afterEach,
	beforeEach,
	describe,
	expect,
	it,
	vi,
} from "vitest";
import { _resetBatchForTesting, emit, initTelemetry } from "../client";

vi.mock("../../lib/logger", () => ({
	default: { warn: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

function mockFetch(): Mock {
	const fetchMock = vi.fn().mockResolvedValue({ ok: true });
	vi.stubGlobal("fetch", fetchMock);
	return fetchMock;
}

beforeEach(() => {
	vi.useFakeTimers();
	_resetBatchForTesting();
});

afterEach(() => {
	vi.useRealTimers();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
});

describe("emit — batching", () => {
	it("does not flush immediately for a single event", () => {
		const fetchMock = mockFetch();
		emit({ type: "nav.page_view", route: "/test" });
		expect(fetchMock).not.toHaveBeenCalled();
	});

	it("flushes after the 5s flush interval", async () => {
		const fetchMock = mockFetch();
		emit({ type: "nav.page_view", route: "/test" });
		await vi.runAllTimersAsync();
		expect(fetchMock).toHaveBeenCalledOnce();
	});

	it("flushes immediately when 20 events are buffered", async () => {
		const fetchMock = mockFetch();
		for (let i = 0; i < 20; i++) {
			emit({ type: "nav.page_view", route: `/page-${i}` });
		}
		await Promise.resolve();
		expect(fetchMock).toHaveBeenCalledOnce();
	});

	it("POSTs to /api/log with events array", async () => {
		const fetchMock = mockFetch();
		emit({ type: "app.error", message: "boom" });
		await vi.runAllTimersAsync();
		expect(fetchMock).toHaveBeenCalledOnce();
		const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
		expect(url).toBe("/api/log");
		const body = JSON.parse(opts.body as string) as { events: unknown[] };
		expect(body.events).toHaveLength(1);
	});

	it("enriches events with session_id and route", async () => {
		const fetchMock = mockFetch();
		emit({ type: "app.error", message: "test" });
		await vi.runAllTimersAsync();
		const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
		const body = JSON.parse(opts.body as string) as {
			events: Array<{ session_id: string; route: string }>;
		};
		expect(body.events[0].session_id).toBeTruthy();
		expect(body.events[0].route).toBeTruthy();
	});
});

describe("emit — sendBeacon on unload", () => {
	it("sendBeacon is called on visibilitychange to hidden", () => {
		const beaconMock = vi.fn().mockReturnValue(true);
		vi.stubGlobal("navigator", { sendBeacon: beaconMock });
		vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
		const cleanup = initTelemetry();
		emit({ type: "nav.page_view", route: "/test" });
		document.dispatchEvent(new Event("visibilitychange"));
		expect(beaconMock).toHaveBeenCalledWith("/api/log", expect.any(String));
		cleanup();
	});
});
