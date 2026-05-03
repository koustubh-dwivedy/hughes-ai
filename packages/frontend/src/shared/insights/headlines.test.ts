import { describe, expect, it } from "vitest";
import type {
	DepositPortfolioData,
	ExecutiveSummaryData,
	OfficerBranchData,
	PastDueData,
} from "../api/dashboardApi";
import {
	depositsHeadline,
	executiveHeadline,
	officerBranchHeadline,
	pastDueHeadline,
} from "./headlines";

const EXEC: ExecutiveSummaryData = {
	total_loans_balance: 44_600_000,
	total_deposits_balance: 51_000_000,
	loan_to_deposit_ratio: 0.87,
	core_deposit_ratio: 0.62,
	blended_past_due_ratio: 0.011,
	monthly_loan_growth: 1_400_000,
	monthly_deposit_growth: 200_000,
	ytd_loan_growth: 4_200_000,
	ytd_deposit_growth: 1_500_000,
	weighted_avg_loan_rate: 0.062,
	weighted_avg_deposit_rate: 0.018,
	rate_spread: 0.044,
	kpi_trend_13_months: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		total_loans_balance: 40_000_000 + i * 200_000,
		total_deposits_balance: 50_000_000,
		blended_past_due_ratio: 0.012,
		rate_spread: 0.04,
	})),
	past_due_aging: [],
};

describe("executiveHeadline", () => {
	it("produces a lede mentioning loans, deposits, past-due", () => {
		const h = executiveHeadline(EXEC);
		expect(h.lede).toMatch(/Loans/);
		expect(h.lede).toMatch(/deposits/);
		expect(h.lede).toMatch(/[Pp]ast-due/);
	});

	it("flags warn tone when past-due is above 1.5%", () => {
		const h = executiveHeadline({ ...EXEC, blended_past_due_ratio: 0.022 });
		expect(h.tone).toBe("warn");
	});

	it("returns 3 callouts", () => {
		expect(executiveHeadline(EXEC).callouts).toHaveLength(3);
	});
});

describe("depositsHeadline", () => {
	const D: DepositPortfolioData = {
		total_deposits: 51_000_000,
		mtd_change: 200_000,
		ytd_change: 1_500_000,
		avg_balance_per_customer: 6_375,
		account_count: 8_000,
		top_25_deposits: [
			{ member_name: "M1", balance: 1_000_000, share_pct: 1.96 },
		],
		deposits_by_branch: [],
		deposit_mix: [
			{ product: "Checking", balance: 30_000_000, share_pct: 0.59 },
			{ product: "Savings", balance: 15_000_000, share_pct: 0.29 },
			{ product: "CDs", balance: 6_000_000, share_pct: 0.12 },
		],
		change_by_product: [],
		new_vs_closed_accounts: {
			opened: { count: 30, amount: 100_000 },
			closed: { count: 10, amount: 50_000 },
		},
	};

	it("includes account count and total deposits in lede", () => {
		const h = depositsHeadline(D);
		expect(h.lede).toMatch(/8,000/);
		expect(h.lede).toMatch(/\$51\.0M/);
	});

	it("warns when one product is over 50%", () => {
		const h = depositsHeadline(D);
		expect(h.callouts.some((c) => c.tone === "warn")).toBe(true);
	});
});

describe("pastDueHeadline", () => {
	const P: PastDueData = {
		past_due_total: 1_400_000,
		past_due_total_delta: 200_000,
		nonaccrual_total: 800_000,
		nonaccrual_total_delta: 0,
		watchlist_count: 8,
		watchlist_count_delta: 1,
		nonperforming_balance: 0,
		nonperforming_balance_delta: 0,
		past_due_by_officer: [
			{ officer_name: "A", balance: 800_000, count: 1 },
			{ officer_name: "B", balance: 400_000, count: 1 },
			{ officer_name: "C", balance: 200_000, count: 1 },
		],
		delinquency_trend_13_months: [
			{
				month: "2026-03-01",
				bucket_30_59: 100,
				bucket_60_89: 100,
				bucket_90_plus: 800,
			},
		],
		past_due_ratio_trend: [
			{ month: "2025-12", ratio: 0.012 },
			{ month: "2026-03", ratio: 0.018 },
		],
	};

	it("flags officer concentration", () => {
		const h = pastDueHeadline(P);
		expect(h.callouts.some((c) => /Concentration/.test(c.label))).toBe(true);
	});

	it("flags 90+ dominance", () => {
		const h = pastDueHeadline(P);
		expect(h.callouts.some((c) => /Late-stage/.test(c.label))).toBe(true);
	});
});

describe("officerBranchHeadline", () => {
	const O: OfficerBranchData = {
		total_loans: 40_000_000,
		account_count: 1_200,
		avg_loan_balance: 33_333,
		top_25_borrowers: [
			{ member_name: "M1", balance: 1_500_000, share_pct: 3.75 },
		],
		loan_mix_donut: [
			{ product: "Auto", balance: 22_000_000, share_pct: 0.55 },
			{ product: "Mortgage", balance: 12_000_000, share_pct: 0.3 },
			{ product: "Cards", balance: 6_000_000, share_pct: 0.15 },
		],
		change_by_type_waterfall: [],
		single_loan_customers_by_type: [],
		combo_balance_rate: [],
		watchlist_trend: Array.from({ length: 13 }, (_, i) => ({
			month: `2025-${String(i + 1).padStart(2, "0")}`,
			count: 5 + i,
			balance: 100_000,
		})),
		tab_data: null,
	};

	it("includes total loans in lede", () => {
		const h = officerBranchHeadline(O);
		expect(h.lede).toMatch(/\$40\.0M/);
	});

	it("warns on top-product concentration", () => {
		const h = officerBranchHeadline(O);
		expect(h.callouts.some((c) => c.tone === "warn")).toBe(true);
	});
});
