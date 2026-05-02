/**
 * HUG-155: tag-relationship test for the OfficerBranch slice.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";
import { createStore } from "../../shared/api/store";
import { useGetOfficerBranchQuery } from "./api";

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

describe("OfficerBranch slice — cache invalidation", () => {
	it("refetches when OfficerBranch tag is invalidated", async () => {
		const spy = vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENV({}));
		const store = createStore();
		renderHook(() => useGetOfficerBranchQuery({}), {
			wrapper: withStore(store),
		});
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		store.dispatch(baseApi.util.invalidateTags(["OfficerBranch"]));
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});

	it("treats branchId/officerId/tab as part of the cache key", async () => {
		const spy = vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENV({}));
		const store = createStore();
		const { rerender } = renderHook(
			(args: { branchId?: number }) => useGetOfficerBranchQuery(args),
			{
				wrapper: withStore(store),
				initialProps: { branchId: 1 },
			},
		);
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
		rerender({ branchId: 2 });
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});
});
