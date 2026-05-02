import "@testing-library/jest-dom";
import { vi } from "vitest";
import * as api from "../shared/api/api";

Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: (query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: () => {},
		removeListener: () => {},
		addEventListener: () => {},
		removeEventListener: () => {},
		dispatchEvent: () => false,
	}),
});

// Bridge: route RTK Query fetches to existing api.* test mocks. Tests
// still spyOn api.getDepositPortfolio etc.; this fetch stub awaits
// that mock, wraps the envelope in a Response, and lets the component
// (now using RTK Query) consume the same fixture.
const URL_TO_API: Array<[RegExp, keyof typeof api]> = [
	[/\/api\/dashboards\/deposit-portfolio/, "getDepositPortfolio"],
	[/\/api\/dashboards\/past-due/, "getPastDue"],
	[/\/api\/dashboards\/officer-branch/, "getOfficerBranch"],
	[/\/api\/dashboards\/executive-summary/, "getExecutiveSummary"],
	[/\/api\/history(\?|$)/, "getHistory"],
	[/\/api\/trust(\?|$)/, "getTrust"],
];

function urlOf(input: RequestInfo | URL): string {
	if (typeof input === "string") return input;
	if (input instanceof URL) return input.href;
	return input.url;
}

function jsonResponse(body: unknown, status = 200): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { "Content-Type": "application/json" },
	});
}

async function delegate(fnName: keyof typeof api): Promise<Response> {
	try {
		const fn = api[fnName] as () => Promise<unknown>;
		return jsonResponse(await fn());
	} catch (err) {
		return jsonResponse(
			{ detail: err instanceof Error ? err.message : "error" },
			500,
		);
	}
}

global.fetch = vi.fn(async (input: RequestInfo | URL) => {
	const url = urlOf(input);
	const match = URL_TO_API.find(([re]) => re.test(url));
	return match ? delegate(match[1]) : jsonResponse({});
}) as unknown as typeof fetch;
