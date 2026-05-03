import { baseApi } from "../../shared/api/client";
import type { GraphResponse, NodeDetail } from "./types";

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getDataModelGraph: build.query<GraphResponse, void>({
			query: () => "/data-model/graph",
		}),
		getDataModelNode: build.query<NodeDetail, string>({
			query: (id) => `/data-model/nodes/${encodeURIComponent(id)}`,
		}),
	}),
	overrideExisting: false,
});

export const { useGetDataModelGraphQuery, useGetDataModelNodeQuery } = slice;
