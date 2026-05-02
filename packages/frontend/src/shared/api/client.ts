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

// Resolve the API base URL absolutely so the WHATWG Request constructor
// (used by fetchBaseQuery internally) works under jsdom — relative paths
// throw "Failed to parse URL" in node-side test environments.
const baseUrl =
	typeof window !== "undefined" ? `${window.location.origin}/api` : "/api";

export const baseApi = createApi({
	reducerPath: "api",
	baseQuery: fetchBaseQuery({ baseUrl }),
	tagTypes: TAG_TYPES,
	endpoints: () => ({}),
});
