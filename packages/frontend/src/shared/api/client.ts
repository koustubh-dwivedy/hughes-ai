import { fetchBaseQuery } from "@reduxjs/toolkit/query";
import {
	buildCreateApi,
	coreModule,
	reactHooksModule,
} from "@reduxjs/toolkit/query/react";
import { TAG_TYPES } from "./tags";

/**
 * createApi built with the same modules as the default react export
 * but constructed via buildCreateApi so we can switch hooks/context
 * without touching every endpoint slice. Slices register endpoints via
 * baseApi.injectEndpoints in their feature folders.
 */
export const createApi = buildCreateApi(coreModule(), reactHooksModule());

export const baseApi = createApi({
	reducerPath: "api",
	baseQuery: fetchBaseQuery({ baseUrl: "/api" }),
	tagTypes: TAG_TYPES,
	endpoints: () => ({}),
});
