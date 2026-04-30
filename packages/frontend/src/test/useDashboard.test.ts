import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useDashboard } from "../hooks/useDashboard";
import type { DashboardEnvelope, DashboardParams } from "../lib/dashboardApi";

function makeEnvelope<T>(data: T): DashboardEnvelope<T> {
	return {
		data,
		as_of_date: "2026-04-01",
		generated_at: "2026-04-01T00:00:00Z",
		audit_id: "00000000-0000-0000-0000-000000000000",
	};
}

type Payload = { value: number };
type FetcherFn = (
	params?: DashboardParams,
) => Promise<DashboardEnvelope<Payload>>;

describe("useDashboard", () => {
	it("returns data on happy path", async () => {
		const fetcher: FetcherFn = vi.fn((_p?: DashboardParams) =>
			Promise.resolve(makeEnvelope({ value: 42 })),
		);
		const { result } = renderHook(() => useDashboard(fetcher));
		expect(result.current.loading).toBe(true);
		await waitFor(() => expect(result.current.loading).toBe(false));
		expect(result.current.data).toEqual({ value: 42 });
		expect(result.current.error).toBeNull();
	});

	it("returns error on fetch failure", async () => {
		const fetcher: FetcherFn = vi.fn((_p?: DashboardParams) =>
			Promise.reject(new Error("HTTP 500")),
		);
		const { result } = renderHook(() => useDashboard(fetcher));
		await waitFor(() => expect(result.current.loading).toBe(false));
		expect(result.current.error).toBe("HTTP 500");
		expect(result.current.data).toBeNull();
	});

	it("aborts in-flight request on unmount", () => {
		let aborted = false;
		const fetcher: FetcherFn = vi.fn(
			(_p?: DashboardParams): Promise<DashboardEnvelope<Payload>> =>
				new Promise(() => {
					/* never resolves */
				}),
		);
		const abortSpy = vi
			.spyOn(AbortController.prototype, "abort")
			.mockImplementation(() => {
				aborted = true;
			});

		const { unmount } = renderHook(() => useDashboard(fetcher));
		unmount();
		expect(aborted).toBe(true);
		abortSpy.mockRestore();
	});

	it("refetches when asOfDate param changes", async () => {
		const fetcher: FetcherFn = vi.fn((_p?: DashboardParams) =>
			Promise.resolve(makeEnvelope({ value: 1 })),
		);
		const { rerender } = renderHook(
			({ asOfDate }: { asOfDate: string }) =>
				useDashboard(fetcher, { asOfDate }),
			{ initialProps: { asOfDate: "2026-03-01" } },
		);
		await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
		rerender({ asOfDate: "2026-04-01" });
		await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
	});

	it("refetch() re-runs the fetcher", async () => {
		const fetcher: FetcherFn = vi.fn((_p?: DashboardParams) =>
			Promise.resolve(makeEnvelope({ value: 1 })),
		);
		const { result } = renderHook(() => useDashboard(fetcher));
		await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
		act(() => {
			result.current.refetch();
		});
		await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
	});
});
