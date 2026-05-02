/**
 * HUG-155: tag-relationship test for the History slice.
 *
 * The Ask mutation invalidates the History tag — submitting a new
 * question must force the history rail to refresh.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";
import { createStore } from "../../shared/api/store";
import { useGetHistoryListQuery } from "./api";

afterEach(() => {
	vi.restoreAllMocks();
});

function withStore(store: ReturnType<typeof createStore>) {
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <ReduxProvider store={store}>{children}</ReduxProvider>;
	};
}

describe("History slice — cache invalidation", () => {
	it("refetches when History tag is invalidated", async () => {
		const spy = vi.spyOn(api, "getHistory").mockResolvedValue([]);
		const store = createStore();
		renderHook(() => useGetHistoryListQuery({ kind: "ask" }), {
			wrapper: withStore(store),
		});
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		store.dispatch(baseApi.util.invalidateTags(["History"]));
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});

	it("treats kind arg as part of the cache key", async () => {
		const spy = vi.spyOn(api, "getHistory").mockResolvedValue([]);
		const store = createStore();
		type Kind = "ask" | "dashboard_audit";
		const { rerender } = renderHook(
			(args: { kind?: Kind }) => useGetHistoryListQuery(args),
			{
				wrapper: withStore(store),
				initialProps: { kind: "ask" as Kind },
			},
		);
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
		rerender({ kind: "dashboard_audit" });
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});
});
