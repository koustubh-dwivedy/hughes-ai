import { baseApi } from "../../shared/api/client";
import type {
	DashboardEnvelope,
	PastDueData,
} from "../../shared/api/dashboardApi";

export interface PastDueArg {
	asOfDate?: string;
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getPastDue: build.query<PastDueData, PastDueArg>({
			query: ({ asOfDate } = {}) => ({
				url: "/dashboards/past-due",
				params: asOfDate ? { as_of_date: asOfDate } : undefined,
			}),
			transformResponse: (env: DashboardEnvelope<PastDueData>) => env.data,
			providesTags: ["PastDue"],
		}),
	}),
	overrideExisting: false,
});

export const { useGetPastDueQuery } = slice;

export function usePastDue(arg: PastDueArg = {}) {
	const result = useGetPastDueQuery(arg);
	return {
		data: result.data ?? null,
		loading: result.isLoading,
		isError: result.isError,
	};
}
