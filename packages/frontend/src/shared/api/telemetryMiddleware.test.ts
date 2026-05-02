import { afterEach, describe, expect, it, vi } from "vitest";
import * as telemetry from "../telemetry/client";
import {
	_resetTelemetryStateForTesting,
	telemetryMiddleware,
} from "./telemetryMiddleware";

afterEach(() => {
	vi.restoreAllMocks();
	_resetTelemetryStateForTesting();
});

const noop = () => undefined;

function pendingAction(endpoint: string, requestId: string) {
	return {
		type: "api/executeQuery/pending",
		meta: {
			arg: { endpointName: endpoint, queryCacheKey: endpoint },
			requestId,
			requestStatus: "pending" as const,
		},
	};
}

function fulfilledAction(endpoint: string, requestId: string, status = 200) {
	return {
		type: "api/executeQuery/fulfilled",
		meta: {
			arg: { endpointName: endpoint, queryCacheKey: endpoint },
			requestId,
			requestStatus: "fulfilled" as const,
			baseQueryMeta: { response: { status } },
		},
		payload: { ok: true },
	};
}

function rejectedAction(endpoint: string, requestId: string, status = 500) {
	return {
		type: "api/executeQuery/rejected",
		meta: {
			arg: { endpointName: endpoint, queryCacheKey: endpoint },
			requestId,
			requestStatus: "rejected" as const,
			baseQueryMeta: { response: { status } },
		},
		error: { message: "boom" },
	};
}

describe("telemetryMiddleware", () => {
	it("emits api.request.started on a pending action", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const handler = telemetryMiddleware({
			getState: noop,
			dispatch: noop,
		} as never)(noop);
		handler(pendingAction("getDepositPortfolio", "req-1"));
		expect(spy).toHaveBeenCalledWith({
			type: "api.request.started",
			endpoint: "getDepositPortfolio",
			method: "GET",
		});
	});

	it("emits api.request.succeeded with cache=miss on first fulfillment", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const handler = telemetryMiddleware({
			getState: noop,
			dispatch: noop,
		} as never)(noop);
		handler(pendingAction("getPastDue", "req-2"));
		handler(fulfilledAction("getPastDue", "req-2"));
		expect(spy).toHaveBeenLastCalledWith(
			expect.objectContaining({
				type: "api.request.succeeded",
				endpoint: "getPastDue",
				status_code: 200,
				cache: "miss",
				retry_count: 0,
			}),
		);
	});

	it("emits api.request.succeeded with cache=hit on a repeat queryCacheKey", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const handler = telemetryMiddleware({
			getState: noop,
			dispatch: noop,
		} as never)(noop);
		handler(pendingAction("getTrust", "req-3"));
		handler(fulfilledAction("getTrust", "req-3"));
		handler(pendingAction("getTrust", "req-4"));
		handler(fulfilledAction("getTrust", "req-4"));
		const secondSucceeded = spy.mock.calls.find(
			(c, i) =>
				i > 1 && (c[0] as { type: string }).type === "api.request.succeeded",
		);
		expect(secondSucceeded?.[0]).toMatchObject({
			type: "api.request.succeeded",
			cache: "hit",
		});
	});

	it("emits api.request.failed on rejected action with the error message", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const handler = telemetryMiddleware({
			getState: noop,
			dispatch: noop,
		} as never)(noop);
		handler(pendingAction("getOfficerBranch", "req-5"));
		handler(rejectedAction("getOfficerBranch", "req-5"));
		expect(spy).toHaveBeenLastCalledWith(
			expect.objectContaining({
				type: "api.request.failed",
				endpoint: "getOfficerBranch",
				status_code: 500,
				error: "boom",
				retry_count: 0,
			}),
		);
	});

	it("ignores non-RTK actions", () => {
		const spy = vi.spyOn(telemetry, "emit");
		const handler = telemetryMiddleware({
			getState: noop,
			dispatch: noop,
		} as never)(noop);
		handler({ type: "some/other/action" });
		expect(spy).not.toHaveBeenCalled();
	});

	it("forwards the action to next so the reducer chain still runs", () => {
		const next = vi.fn();
		const handler = telemetryMiddleware({
			getState: noop,
			dispatch: noop,
		} as never)(next);
		const action = pendingAction("getExecutiveSummary", "req-7");
		handler(action);
		expect(next).toHaveBeenCalledWith(action);
	});
});
