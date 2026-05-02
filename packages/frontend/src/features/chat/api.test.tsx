/**
 * HUG-155: tag-relationship test for the Ask mutation slice.
 *
 * usePostAskMutation declares invalidatesTags: ["History"]. After a
 * successful mutation, any active getHistoryList subscription should
 * automatically refetch.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { createStore } from "../../shared/api/store";
import { useGetHistoryListQuery } from "../history/api";
import { usePostAskMutation } from "./api";

afterEach(() => {
	vi.restoreAllMocks();
});

function withStore(store: ReturnType<typeof createStore>) {
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <ReduxProvider store={store}>{children}</ReduxProvider>;
	};
}

describe("Chat slice — Ask mutation invalidates History", () => {
	it("postAsk triggers a refetch on the active getHistoryList query", async () => {
		const historySpy = vi.spyOn(api, "getHistory").mockResolvedValue([]);
		const store = createStore();
		const wrapper = withStore(store);

		// Subscribe to history first — counts as fetch #1.
		renderHook(() => useGetHistoryListQuery({ kind: "ask" }), { wrapper });
		await waitFor(() => expect(historySpy).toHaveBeenCalledTimes(1));

		// Fire the mutation. The test fetch bridge returns an empty body
		// for /api/ask (it's not in URL_TO_API), but RTK still resolves
		// the mutation and processes invalidatesTags["History"] — that's
		// the contract under test.
		const { result } = renderHook(() => usePostAskMutation(), { wrapper });
		await act(async () => {
			await result.current[0]({ question: "How many?" }).unwrap();
		});

		// History refetches because Ask invalidates the History tag
		await waitFor(() => expect(historySpy).toHaveBeenCalledTimes(2));
	});
});
