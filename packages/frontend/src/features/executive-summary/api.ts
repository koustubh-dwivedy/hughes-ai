import { baseApi } from "../../shared/api/client";
import type {
	DashboardEnvelope,
	ExecutiveSummaryData,
} from "../../shared/api/dashboardApi";

export interface ExecutiveSummaryArg {
	asOfDate?: string;
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getExecutiveSummary: build.query<ExecutiveSummaryData, ExecutiveSummaryArg>(
			{
				query: ({ asOfDate } = {}) => ({
					url: "/dashboards/executive-summary",
					params: asOfDate ? { as_of_date: asOfDate } : undefined,
				}),
				transformResponse: (env: DashboardEnvelope<ExecutiveSummaryData>) =>
					env.data,
				providesTags: ["ExecutiveSummary"],
			},
		),
	}),
	overrideExisting: false,
});

export const { useGetExecutiveSummaryQuery } = slice;

export function useExecutiveSummary(arg: ExecutiveSummaryArg = {}) {
	const result = useGetExecutiveSummaryQuery(arg);
	return {
		data: result.data ?? null,
		loading: result.isLoading,
		isError: result.isError,
	};
}
