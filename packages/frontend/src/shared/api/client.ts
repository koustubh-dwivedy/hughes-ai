import { fetchBaseQuery } from "@reduxjs/toolkit/query";
import {
	buildCreateApi,
	coreModule,
	reactHooksModule,
} from "@reduxjs/toolkit/query/react";
import { SESSION_HEADER, getSessionId } from "../telemetry/session";
import { USER_HEADER, getUserId } from "../telemetry/user";
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
	baseQuery: fetchBaseQuery({
		baseUrl,
		prepareHeaders: (headers) => {
			// X-Hughes-Session: ephemeral per-tab id used purely for
			// log correlation across the stack.
			headers.set(SESSION_HEADER, getSessionId());
			// X-Hughes-User: durable per-browser id used to filter
			// thread ownership so chat history persists across tab close
			// (HUG-205). Both headers travel together on every request.
			headers.set(USER_HEADER, getUserId());
			return headers;
		},
	}),
	tagTypes: TAG_TYPES,
	endpoints: () => ({}),
});
