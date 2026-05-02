import { renderHook, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useGetDepositPortfolioQuery } from "../../features/deposit-portfolio/api";
import { useGetExecutiveSummaryQuery } from "../../features/executive-summary/api";
import { useGetOfficerBranchQuery } from "../../features/officer-branch/api";
import { useGetPastDueQuery } from "../../features/past-due/api";
import * as api from "./api";
import { baseApi } from "./client";
import { createStore } from "./store";

// biome-ignore lint/suspicious/noExplicitAny: tests only need the envelope shape, not the inner data fields
const ENV = (data: object): any => ({
	data,
	as_of_date: "2026-04-30",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test",
});

function withStore(store: ReturnType<typeof createStore>) {
	function Wrapper({ children }: { children: React.ReactNode }) {
		return <ReduxProvider store={store}>{children}</ReduxProvider>;
	}
	return Wrapper;
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("RTK Query — cache invalidation by tag", () => {
	it.each([
		[
			"DepositPortfolio",
			"getDepositPortfolio" as const,
			useGetDepositPortfolioQuery,
		],
		["PastDue", "getPastDue" as const, useGetPastDueQuery],
		["OfficerBranch", "getOfficerBranch" as const, useGetOfficerBranchQuery],
		[
			"ExecutiveSummary",
			"getExecutiveSummary" as const,
			useGetExecutiveSummaryQuery,
		],
	])(
		"%s endpoint refetches when its tag is invalidated",
		async (tag, fnName, useQuery) => {
			const spy = vi.spyOn(api, fnName).mockResolvedValue(ENV({}));
			const store = createStore();
			renderHook(() => useQuery({}), { wrapper: withStore(store) });
			await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

			store.dispatch(
				baseApi.util.invalidateTags([
					tag as Parameters<typeof baseApi.util.invalidateTags>[0][number],
				]),
			);
			await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
		},
	);
});

describe("RTK Query — as_of_date triggers refetch", () => {
	it("changing asOfDate arg fires a new request", async () => {
		const spy = vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENV({}));
		const store = createStore();
		const { rerender } = renderHook(
			({ asOfDate }: { asOfDate: string }) =>
				useGetDepositPortfolioQuery({ asOfDate }),
			{ wrapper: withStore(store), initialProps: { asOfDate: "2026-04-30" } },
		);
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		rerender({ asOfDate: "2026-05-01" });
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
	});

	it("repeating same asOfDate uses cache (no refetch)", async () => {
		const spy = vi.spyOn(api, "getPastDue").mockResolvedValue(ENV({}));
		const store = createStore();
		const { rerender } = renderHook(
			({ asOfDate }: { asOfDate: string }) => useGetPastDueQuery({ asOfDate }),
			{ wrapper: withStore(store), initialProps: { asOfDate: "2026-04-30" } },
		);
		await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

		rerender({ asOfDate: "2026-04-30" });
		// give RTK a tick to potentially refetch
		await new Promise((r) => setTimeout(r, 20));
		expect(spy).toHaveBeenCalledTimes(1);
	});
});
