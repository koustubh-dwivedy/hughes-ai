import { baseApi } from "../../shared/api/client";
import type {
	DashboardEnvelope,
	DepositPortfolioData,
} from "../../shared/api/dashboardApi";

export interface DepositPortfolioArg {
	asOfDate?: string;
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getDepositPortfolio: build.query<DepositPortfolioData, DepositPortfolioArg>(
			{
				query: ({ asOfDate } = {}) => ({
					url: "/dashboards/deposit-portfolio",
					params: asOfDate ? { as_of_date: asOfDate } : undefined,
				}),
				transformResponse: (env: DashboardEnvelope<DepositPortfolioData>) =>
					env.data,
				providesTags: ["DepositPortfolio"],
			},
		),
	}),
	overrideExisting: false,
});

export const { useGetDepositPortfolioQuery } = slice;

export function useDepositPortfolio(arg: DepositPortfolioArg = {}) {
	const result = useGetDepositPortfolioQuery(arg);
	return {
		data: result.data ?? null,
		loading: result.isLoading,
		isError: result.isError,
	};
}
