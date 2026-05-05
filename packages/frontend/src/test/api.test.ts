import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	getDepositPortfolio,
	getExecutiveSummary,
	getHistory,
	getOfficerBranch,
	getPastDue,
	getTrust,
} from "../shared/api/api";

let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown, status = 200): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { "Content-Type": "application/json" },
	});
}

beforeEach(() => {
	fetchMock = vi.fn();
	vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
	vi.unstubAllGlobals();
});

describe("getHistory", () => {
	it("uses the default limit of 20", async () => {
		fetchMock.mockResolvedValue(jsonResponse([]));
		await getHistory();
		expect(fetchMock.mock.calls[0][0]).toBe("/api/history?limit=20");
	});

	it("respects an explicit limit", async () => {
		fetchMock.mockResolvedValue(jsonResponse([]));
		await getHistory(5);
		expect(fetchMock.mock.calls[0][0]).toBe("/api/history?limit=5");
	});
});

describe("getTrust", () => {
	it("hits /api/trust", async () => {
		fetchMock.mockResolvedValue(jsonResponse({}));
		await getTrust();
		expect(fetchMock.mock.calls[0][0]).toBe("/api/trust");
	});
});

describe("dashboard fetchers", () => {
	beforeEach(() => {
		fetchMock.mockResolvedValue(jsonResponse({ data: {} }));
	});

	it("getDepositPortfolio omits qs when no asOfDate", async () => {
		await getDepositPortfolio();
		expect(fetchMock.mock.calls[0][0]).toBe(
			"/api/dashboards/deposit-portfolio",
		);
	});

	it("getDepositPortfolio appends as_of_date when provided", async () => {
		await getDepositPortfolio({ asOfDate: "2026-03-01" });
		expect(fetchMock.mock.calls[0][0]).toBe(
			"/api/dashboards/deposit-portfolio?as_of_date=2026-03-01",
		);
	});

	it("getPastDue uses the past-due path", async () => {
		await getPastDue({ asOfDate: "2026-03-01" });
		expect(fetchMock.mock.calls[0][0]).toBe(
			"/api/dashboards/past-due?as_of_date=2026-03-01",
		);
	});

	it("getExecutiveSummary uses the executive-summary path", async () => {
		await getExecutiveSummary();
		expect(fetchMock.mock.calls[0][0]).toBe(
			"/api/dashboards/executive-summary",
		);
	});

	it("getOfficerBranch composes all four optional params", async () => {
		await getOfficerBranch({
			asOfDate: "2026-03-01",
			branchId: 7,
			officerId: "o-99",
			tab: "new",
		});
		const url = fetchMock.mock.calls[0][0] as string;
		expect(url.startsWith("/api/dashboards/officer-branch?")).toBe(true);
		expect(url).toContain("as_of_date=2026-03-01");
		expect(url).toContain("branch_id=7");
		expect(url).toContain("officer_id=o-99");
		expect(url).toContain("tab=new");
	});

	it("getOfficerBranch omits qs when params are absent", async () => {
		await getOfficerBranch();
		expect(fetchMock.mock.calls[0][0]).toBe("/api/dashboards/officer-branch");
	});
});

