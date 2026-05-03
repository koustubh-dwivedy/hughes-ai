import { baseApi } from "../../shared/api/client";

export interface AvailableMonths {
	months: string[];
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getAvailableMonths: build.query<AvailableMonths, string>({
			query: (surface) => ({
				url: "/dashboards/available-months",
				params: { surface },
			}),
		}),
	}),
	overrideExisting: false,
});

export const { useGetAvailableMonthsQuery } = slice;
