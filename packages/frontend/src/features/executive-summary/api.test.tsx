/**
 * HUG-155: tag-relationship test for the ExecutiveSummary slice.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";
import { createStore } from "../../shared/api/store";
import { useGetExecutiveSummaryQuery } from "./api";

// biome-ignore lint/suspicious/noExplicitAny: integration tests use partial fixtures
const ENV = (data: object): any => ({
	data,
	as_of_date: "2026-04-30",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test",
});

afterEach(() => {
	vi.restoreAllMocks();
});

function withStore(store: ReturnType<typeof createStore>) {
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <ReduxProvider store={store}>{children}</ReduxProvider>;
	};
}

describe("ExecutiveSummary slice — cache invalidation", () => {
	it("refetches when ExecutiveSummary tag is invalidated", async () => {
		const spy = vi.spyOn(api, "getExecutiveSummary").mockResolvedValue(ENV({}));
		const store = createStore();
		renderHook(() => useGetExecutiveSummaryQuery({}), {
			wrapper: withStore(store),
		});
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		store.dispatch(baseApi.util.invalidateTags(["ExecutiveSummary"]));
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});

	it("does NOT refetch on unrelated tag invalidation", async () => {
		const spy = vi.spyOn(api, "getExecutiveSummary").mockResolvedValue(ENV({}));
		const store = createStore();
		renderHook(() => useGetExecutiveSummaryQuery({}), {
			wrapper: withStore(store),
		});
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		store.dispatch(baseApi.util.invalidateTags(["History"]));
		await new Promise((r) => setTimeout(r, 20));
		expect(spy).toHaveBeenCalledTimes(1);
	});
});
