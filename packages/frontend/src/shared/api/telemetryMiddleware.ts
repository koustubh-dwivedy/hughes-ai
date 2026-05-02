import type { Middleware } from "@reduxjs/toolkit";
import { emit } from "../telemetry/client";

interface RtkQueryActionMeta {
	arg: {
		endpointName: string;
		queryCacheKey?: string;
		type?: "query" | "mutation";
	};
	requestId: string;
	requestStatus: "pending" | "fulfilled" | "rejected";
	baseQueryMeta?: { response?: { status?: number } };
}

interface MaybeRtkAction {
	type?: string;
	meta?: RtkQueryActionMeta;
	error?: { message?: string };
}

const startedAt = new Map<string, number>();
const seenCacheKeys = new Set<string>();

function isRtkQueryAction(action: unknown): action is MaybeRtkAction & {
	meta: RtkQueryActionMeta;
} {
	if (typeof action !== "object" || action === null) return false;
	const m = (action as MaybeRtkAction).meta;
	return (
		typeof m === "object" &&
		m !== null &&
		typeof m.arg?.endpointName === "string" &&
		typeof m.requestStatus === "string"
	);
}

function emitStarted(action: MaybeRtkAction & { meta: RtkQueryActionMeta }) {
	startedAt.set(action.meta.requestId, Date.now());
	emit({
		type: "api.request.started",
		endpoint: action.meta.arg.endpointName,
		method: action.meta.arg.type === "mutation" ? "POST" : "GET",
	});
}

function emitSucceeded(action: MaybeRtkAction & { meta: RtkQueryActionMeta }) {
	const start = startedAt.get(action.meta.requestId) ?? Date.now();
	const duration = Date.now() - start;
	startedAt.delete(action.meta.requestId);
	const cacheKey =
		action.meta.arg.queryCacheKey ?? action.meta.arg.endpointName;
	const cache = seenCacheKeys.has(cacheKey) ? "hit" : "miss";
	seenCacheKeys.add(cacheKey);
	emit({
		type: "api.request.succeeded",
		endpoint: action.meta.arg.endpointName,
		status_code: action.meta.baseQueryMeta?.response?.status ?? 200,
		duration_ms: duration,
		cache,
		retry_count: 0,
	});
}

function emitFailed(action: MaybeRtkAction & { meta: RtkQueryActionMeta }) {
	const start = startedAt.get(action.meta.requestId) ?? Date.now();
	const duration = Date.now() - start;
	startedAt.delete(action.meta.requestId);
	emit({
		type: "api.request.failed",
		endpoint: action.meta.arg.endpointName,
		status_code: action.meta.baseQueryMeta?.response?.status,
		error: action.error?.message ?? "unknown",
		duration_ms: duration,
		retry_count: 0,
	});
}

function routeByStatus(
	action: MaybeRtkAction & { meta: RtkQueryActionMeta },
): void {
	if (action.meta.requestStatus === "pending") emitStarted(action);
	else if (action.meta.requestStatus === "fulfilled") emitSucceeded(action);
	else if (action.meta.requestStatus === "rejected") emitFailed(action);
}

/**
 * Redux middleware: turn RTK Query lifecycle actions into telemetry
 * events so we have a single timeline of every request's start, end,
 * duration, status, and cache state. Attached in `store.ts` via
 * `configureStore({ middleware: getDefault().concat(... ) })`.
 */
export const telemetryMiddleware: Middleware = () => (next) => (action) => {
	if (isRtkQueryAction(action)) routeByStatus(action);
	return next(action);
};

export function _resetTelemetryStateForTesting(): void {
	startedAt.clear();
	seenCacheKeys.clear();
}
