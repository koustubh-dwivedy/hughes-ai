import type { AskResponse } from "../../shared/api/api";
import { baseApi } from "../../shared/api/client";

export interface AskArg {
	question: string;
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		postAsk: build.mutation<AskResponse, AskArg>({
			query: ({ question }) => ({
				url: "/ask",
				method: "POST",
				body: { question },
			}),
			invalidatesTags: ["History"],
		}),
	}),
	overrideExisting: false,
});

export const { usePostAskMutation } = slice;
