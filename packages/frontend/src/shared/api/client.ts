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
//
// HUG-260: production split — SPA at app.tryhughes.com calls the API at
// api.tryhughes.com directly (Cloud Run domain mapping), bypassing
// Firebase Hosting's `rewrites.run` 60s ceiling. Local dev (and tests in
// jsdom, which set window.location.hostname=localhost) stay same-origin
// so Vite's `/api` proxy keeps working without CORS.
function _resolveBaseUrl(): string {
	if (typeof window === "undefined") return "/api";
	const host = window.location.hostname;
	if (host === "localhost" || host === "127.0.0.1") {
		return `${window.location.origin}/api`;
	}
	// app.tryhughes.com → api.tryhughes.com (any future `app.*` → `api.*`).
	const apiHost = host.startsWith("app.")
		? `api.${host.slice(4)}`
		: `api.${host}`;
	return `https://${apiHost}/api`;
}

export const baseUrl = _resolveBaseUrl();

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
