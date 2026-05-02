import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	getDepositPortfolio,
	getExecutiveSummary,
	getHistory,
	getOfficerBranch,
	getPastDue,
	getTrust,
	historyDetailToAskResponse,
	postAsk,
	postRerun,
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

describe("postAsk", () => {
	it("POSTs to /api/ask with JSON body", async () => {
		fetchMock.mockResolvedValue(jsonResponse({ rows: [] }));
		await postAsk("how many loans");
		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toBe("/api/ask");
		expect(init.method).toBe("POST");
		// fetchJson now wraps headers in a Headers instance to inject
		// X-Hughes-Session — use the Headers API instead of object access.
		const headers = init.headers as Headers;
		expect(headers.get("Content-Type")).toBe("application/json");
		expect(headers.get("X-Hughes-Session")).toMatch(/^[0-9a-f-]{36}$/);
		expect(JSON.parse(init.body)).toEqual({ question: "how many loans" });
	});

	it("throws on non-2xx with HTTP <status>", async () => {
		fetchMock.mockResolvedValue(jsonResponse({ detail: "boom" }, 500));
		await expect(postAsk("q")).rejects.toThrow("HTTP 500");
	});
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

describe("postRerun", () => {
	it("POSTs to /api/history/<id>/rerun", async () => {
		fetchMock.mockResolvedValue(jsonResponse({}));
		await postRerun("abc-123");
		expect(fetchMock.mock.calls[0][0]).toBe("/api/history/abc-123/rerun");
		expect(fetchMock.mock.calls[0][1].method).toBe("POST");
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

describe("historyDetailToAskResponse", () => {
	it("flattens nested answer/lineage JSON into AskResponse", () => {
		const out = historyDetailToAskResponse({
			id: "id-1",
			question: "q",
			sql: "SELECT 1",
			created_at: "2026-01-01",
			answer_json: {
				explanation: "ok",
				rows: [{ a: 1 }],
				columns: ["a"],
			},
			assumptions: ["A1"],
			caveats: ["C1"],
			lineage_json: { tables_used: ["t1"] },
		});
		expect(out.request_id).toBe("id-1");
		expect(out.sql).toBe("SELECT 1");
		expect(out.explanation).toBe("ok");
		expect(out.tables_used).toEqual(["t1"]);
		expect(out.rows).toEqual([{ a: 1 }]);
		expect(out.columns).toEqual(["a"]);
		expect(out.clarification).toBeNull();
	});

	it("provides safe defaults when fields are missing", () => {
		const out = historyDetailToAskResponse({
			id: "id-2",
			question: "q",
			sql: "SELECT 1",
			created_at: "2026-01-01",
			answer_json: {},
			assumptions: [],
			caveats: [],
			lineage_json: {},
		});
		expect(out.explanation).toBeNull();
		expect(out.tables_used).toEqual([]);
		expect(out.rows).toEqual([]);
		expect(out.columns).toEqual([]);
	});
});
