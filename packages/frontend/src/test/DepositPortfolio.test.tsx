import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DepositPortfolio from "../features/deposits";
import type { DepositPortfolioData } from "../shared/api/dashboardApi";
import type { UseDashboardResult } from "../shared/hooks/useDashboard";
import { renderWithProviders } from "./test-utils";

vi.mock("../shared/hooks/useDashboard");
import { useDashboard } from "../shared/hooks/useDashboard";

const fixture: DepositPortfolioData = {
	total_deposits: 150_000_000,
	mtd_change: 2_500_000,
	ytd_change: 8_000_000,
	avg_balance_per_customer: 12_500,
	account_count: 12_000,
	top_25_deposits: [
		{ member_name: "Acme Corp", balance: 5_000_000, share_pct: 3.3 },
	],
	deposits_by_branch: [
		{ branch_name: "Main", balance: 80_000_000 },
		{ branch_name: "East", balance: 70_000_000 },
	],
	deposit_mix: [
		{ product: "Savings", balance: 90_000_000, share_pct: 60.0 },
		{ product: "Checking", balance: 60_000_000, share_pct: 40.0 },
	],
	change_by_product: [
		{ product: "Savings", delta: 1_500_000 },
		{ product: "Checking", delta: 1_000_000 },
	],
	new_vs_closed_accounts: {
		opened: { count: 120, amount: 1_200_000 },
		closed: { count: 45, amount: 350_000 },
	},
};

function mockHook(
	overrides: Partial<UseDashboardResult<DepositPortfolioData>>,
) {
	vi.mocked(useDashboard).mockReturnValue({
		data: null,
		loading: false,
		error: null,
		refetch: vi.fn(),
		...overrides,
	});
}

describe("DepositPortfolio", () => {
	it("renders KPI tiles from fixture data", () => {
		mockHook({ data: fixture });
		renderWithProviders(<DepositPortfolio />);
		expect(screen.getByText("Total Deposits")).toBeInTheDocument();
		expect(screen.getByText("$150.0M")).toBeInTheDocument();
		expect(screen.getByText("12,000")).toBeInTheDocument();
	});

	it("shows loading state via DashboardShell", () => {
		mockHook({ loading: true });
		renderWithProviders(<DepositPortfolio />);
		expect(screen.getByLabelText("loading dashboard")).toBeInTheDocument();
	});

	it("shows error state via DashboardShell", () => {
		mockHook({ error: "HTTP 500" });
		renderWithProviders(<DepositPortfolio />);
		expect(screen.getByRole("alert")).toHaveTextContent("HTTP 500");
	});
});
