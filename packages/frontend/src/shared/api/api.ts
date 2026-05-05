import { SESSION_HEADER, getSessionId } from "../telemetry/session";
import type {
	DashboardEnvelope,
	DashboardParams,
	DepositPortfolioData,
	ExecutiveSummaryData,
	OfficerBranchData,
	PastDueData,
} from "./dashboardApi";

const BASE = "/api";

export interface HistorySummary {
	id: string;
	question: string;
	sql: string;
	created_at: string;
}

export interface TrustResponse {
	origence_row_count: number;
	symitar_row_count: number;
	reconciliation_match_rate: number;
	known_caveats: string[];
	as_of_date?: string;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
	const headers = new Headers(init?.headers);
	headers.set(SESSION_HEADER, getSessionId());
	const res = await fetch(url, { ...init, headers });
	if (!res.ok) throw new Error(`HTTP ${res.status}`);
	return res.json() as Promise<T>;
}

export function getHistory(limit = 20): Promise<HistorySummary[]> {
	return fetchJson<HistorySummary[]>(`${BASE}/history?limit=${limit}`);
}

export function getTrust(): Promise<TrustResponse> {
	return fetchJson<TrustResponse>(`${BASE}/trust`);
}

export interface AnswerJson {
	explanation?: string;
	rows?: Record<string, unknown>[];
	columns?: string[];
}

export interface LineageJson {
	tables_used?: string[];
}

export interface HistoryDetail {
	id: string;
	question: string;
	sql: string;
	created_at: string;
	answer_json: AnswerJson;
	assumptions: string[];
	caveats: string[];
	lineage_json: LineageJson;
}

export function getHistoryDetail(id: string): Promise<HistoryDetail> {
	return fetchJson<HistoryDetail>(`${BASE}/history/${id}`);
}

// ── Dashboard fetchers ────────────────────────────────────────────────────────

export function getDepositPortfolio(
	params?: DashboardParams,
): Promise<DashboardEnvelope<DepositPortfolioData>> {
	const qs = params?.asOfDate ? `?as_of_date=${params.asOfDate}` : "";
	return fetchJson(`${BASE}/dashboards/deposit-portfolio${qs}`);
}

export function getPastDue(
	params?: DashboardParams,
): Promise<DashboardEnvelope<PastDueData>> {
	const qs = params?.asOfDate ? `?as_of_date=${params.asOfDate}` : "";
	return fetchJson(`${BASE}/dashboards/past-due${qs}`);
}

export function getOfficerBranch(
	params?: DashboardParams,
): Promise<DashboardEnvelope<OfficerBranchData>> {
	const p = new URLSearchParams();
	if (params?.asOfDate) p.set("as_of_date", params.asOfDate);
	if (params?.branchId !== undefined)
		p.set("branch_id", String(params.branchId));
	if (params?.officerId) p.set("officer_id", params.officerId);
	if (params?.tab) p.set("tab", params.tab);
	const qs = p.size > 0 ? `?${p.toString()}` : "";
	return fetchJson(`${BASE}/dashboards/officer-branch${qs}`);
}

export function getExecutiveSummary(
	params?: DashboardParams,
): Promise<DashboardEnvelope<ExecutiveSummaryData>> {
	const qs = params?.asOfDate ? `?as_of_date=${params.asOfDate}` : "";
	return fetchJson(`${BASE}/dashboards/executive-summary${qs}`);
}

