import type { HistoryDetail, HistorySummary } from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";

export interface HistoryListArg {
	limit?: number;
	kind?: "ask" | "dashboard_audit";
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getHistoryList: build.query<HistorySummary[], HistoryListArg>({
			query: ({ limit = 20, kind } = {}) => ({
				url: "/history",
				params: kind ? { limit, kind } : { limit },
			}),
			providesTags: ["History"],
		}),
		getHistoryDetail: build.query<HistoryDetail, string>({
			query: (id) => ({ url: `/history/${id}` }),
			providesTags: ["History"],
		}),
	}),
	overrideExisting: false,
});

export const { useGetHistoryListQuery, useGetHistoryDetailQuery } = slice;
