/**
 * HUG-155: tag-relationship test for the Trust slice.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";
import { createStore } from "../../shared/api/store";
import { useGetTrustQuery } from "./api";

const TRUST_FIXTURE = {
	origence_row_count: 1,
	symitar_row_count: 1,
	reconciliation_match_rate: 1,
	known_caveats: [],
};

afterEach(() => {
	vi.restoreAllMocks();
});

function withStore(store: ReturnType<typeof createStore>) {
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <ReduxProvider store={store}>{children}</ReduxProvider>;
	};
}

describe("Trust slice — cache invalidation", () => {
	it("refetches when Trust tag is invalidated", async () => {
		const spy = vi.spyOn(api, "getTrust").mockResolvedValue(TRUST_FIXTURE);
		const store = createStore();
		renderHook(() => useGetTrustQuery(), { wrapper: withStore(store) });
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		store.dispatch(baseApi.util.invalidateTags(["Trust"]));
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});

	it("does NOT refetch on unrelated tag invalidation", async () => {
		const spy = vi.spyOn(api, "getTrust").mockResolvedValue(TRUST_FIXTURE);
		const store = createStore();
		renderHook(() => useGetTrustQuery(), { wrapper: withStore(store) });
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		store.dispatch(baseApi.util.invalidateTags(["DepositPortfolio"]));
		await new Promise((r) => setTimeout(r, 20));
		expect(spy).toHaveBeenCalledTimes(1);
	});
});
