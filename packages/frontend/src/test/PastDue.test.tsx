import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PastDue, { buildDelinquencyTrend } from "../features/past-due";
import type { PastDueData } from "../shared/api/dashboardApi";
import { renderWithProviders } from "./test-utils";

vi.mock("../features/past-due/api");
import { usePastDue } from "../features/past-due/api";

const fixture: PastDueData = {
	past_due_total: 2_500_000,
	past_due_total_delta: 100_000,
	nonaccrual_total: 500_000,
	nonaccrual_total_delta: -50_000,
	watchlist_count: 15,
	watchlist_count_delta: 2,
	nonperforming_balance: 1_200_000,
	nonperforming_balance_delta: 80_000,
	past_due_by_officer: [{ officer_name: "Alice", balance: 800_000, count: 5 }],
	delinquency_trend_13_months: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		bucket_30_59: 100_000 + i * 10_000,
		bucket_60_89: 50_000 + i * 5_000,
		bucket_90_plus: 25_000 + i * 2_500,
	})),
	past_due_ratio_trend: [{ month: "2025-01", ratio: 0.023 }],
};

interface MockShape {
	data?: PastDueData | null;
	loading?: boolean;
	isError?: boolean;
}
function mockHook(overrides: MockShape) {
	vi.mocked(usePastDue).mockReturnValue({
		data: null,
		loading: false,
		isError: false,
		...overrides,
	});
}

describe("PastDue", () => {
	it("renders KPI tiles from fixture data", () => {
		mockHook({ data: fixture });
		renderWithProviders(<PastDue />);
		expect(screen.getByText("Past Due Total")).toBeInTheDocument();
		expect(screen.getByText("$2.5M")).toBeInTheDocument();
		expect(screen.getByText("Watchlist")).toBeInTheDocument();
	});

	it("positive past_due_total_delta shows red delta with formatted currency", () => {
		mockHook({ data: fixture });
		renderWithProviders(<PastDue />);
		const deltaEl = screen.getByText("↑ $100K");
		expect(deltaEl).toHaveStyle({ color: "#dc2626" });
	});

	it("buildDelinquencyTrend maps 13 months with correct keys", () => {
		const result = buildDelinquencyTrend(fixture);
		expect(result).toHaveLength(13);
		expect(result[0]).toMatchObject({
			period: "2025-01",
			"30-59": 100_000,
			"60-89": 50_000,
			"90+": 25_000,
		});
	});
});
