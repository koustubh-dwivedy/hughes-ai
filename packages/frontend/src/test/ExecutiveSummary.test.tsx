import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ExecutiveSummary, { buildAgingBar } from "../features/executive";
import type { ExecutiveSummaryData } from "../shared/api/dashboardApi";
import type { UseDashboardResult } from "../shared/hooks/useDashboard";

vi.mock("../shared/hooks/useDashboard");
import { useDashboard } from "../shared/hooks/useDashboard";

const fixture: ExecutiveSummaryData = {
	total_loans_balance: 42_500_000,
	total_deposits_balance: 35_200_000,
	loan_to_deposit_ratio: 0.85,
	core_deposit_ratio: 0.72,
	blended_past_due_ratio: 0.023,
	monthly_loan_growth: 1_200_000,
	monthly_deposit_growth: 800_000,
	ytd_loan_growth: 4_500_000,
	ytd_deposit_growth: 3_100_000,
	weighted_avg_loan_rate: 0.062,
	weighted_avg_deposit_rate: 0.018,
	rate_spread: 0.044,
	kpi_trend_13_months: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		total_loans_balance: 40_000_000 + i * 200_000,
		total_deposits_balance: 34_000_000 + i * 100_000,
		blended_past_due_ratio: 0.02 + i * 0.001,
		rate_spread: 0.04 + i * 0.001,
	})),
	past_due_aging: [
		{ bucket: "15-29 DPD", balance: 500_000, loan_count: 12 },
		{ bucket: "30-59 DPD", balance: 300_000, loan_count: 8 },
		{ bucket: "60-89 DPD", balance: 150_000, loan_count: 4 },
		{ bucket: "90+ DPD", balance: 80_000, loan_count: 2 },
	],
};

function mockHook(
	overrides: Partial<UseDashboardResult<ExecutiveSummaryData>>,
) {
	vi.mocked(useDashboard).mockReturnValue({
		data: null,
		loading: false,
		error: null,
		refetch: vi.fn(),
		...overrides,
	});
}

describe("ExecutiveSummary", () => {
	it("renders without error", () => {
		mockHook({ data: fixture });
		render(<ExecutiveSummary />);
		expect(screen.getByText("Executive Summary")).toBeInTheDocument();
	});

	it("renders all 9 KPI tile labels", () => {
		mockHook({ data: fixture });
		render(<ExecutiveSummary />);
		for (const label of [
			"Total Loans",
			"Total Deposits",
			"MTD Loan Growth",
			"YTD Loan Growth",
			"MTD Deposit Growth",
			"YTD Deposit Growth",
			"Past Due Ratio",
			"Loan-to-Deposit",
			"Core Deposit Ratio",
		]) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it("buildAgingBar returns 4 buckets", () => {
		const result = buildAgingBar(fixture);
		expect(result).toHaveLength(4);
		expect(result[0]).toMatchObject({ period: "15-29 DPD" });
		expect(result[3]).toMatchObject({ period: "90+ DPD" });
	});
});
