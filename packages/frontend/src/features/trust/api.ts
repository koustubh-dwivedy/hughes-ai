import type { TrustResponse } from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getTrust: build.query<TrustResponse, void>({
			query: () => ({ url: "/trust" }),
			providesTags: ["Trust"],
		}),
	}),
	overrideExisting: false,
});

export const { useGetTrustQuery } = slice;
