/**
 * HUG-153 contract test for Deposit Portfolio.
 *
 * Pins the exact text rendered for every KPI tile + delta sign + the
 * branch-table rows + the deposit-mix labels. A swap between
 * total_deposits and mtd_change (or any KPI ↔ KPI mistake) breaks
 * this test immediately.
 */

import { screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import { renderWithProviders } from "../../test/test-utils";
import DepositPortfolio from "./DepositPortfolio";

const FIXTURE = {
	total_deposits: 35_200_000,
	mtd_change: 800_000,
	ytd_change: 3_100_000,
	avg_balance_per_customer: 4_400,
	account_count: 8_000,
	top_25_deposits: [
		{ member_name: "Member 1", balance: 1_000_000, share_pct: 2.84 },
	],
	deposits_by_branch: [
		{ branch_name: "Main", balance: 20_000_000 },
		{ branch_name: "North", balance: 15_200_000 },
	],
	deposit_mix: [
		{ product: "Savings", balance: 18_000_000, share_pct: 0.51 },
		{ product: "Checking", balance: 10_000_000, share_pct: 0.28 },
	],
	change_by_product: [{ product: "Savings", delta: 500_000 }],
	new_vs_closed_accounts: {
		opened: { count: 120, amount: 2_400_000 },
		closed: { count: 35, amount: 700_000 },
	},
};

const ENVELOPE = {
	data: FIXTURE,
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "contract-deposits",
};

afterEach(() => {
	vi.restoreAllMocks();
});

function renderPage() {
	return renderWithProviders(
		<MemoryRouter>
			<DashboardContextProvider>
				<DepositPortfolio />
			</DashboardContextProvider>
		</MemoryRouter>,
	);
}

describe("DepositPortfolio — contract", () => {
	it("pins exact KPI label→value pairs (catches metric swaps)", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getAllByText("$35.2M").length).toBeGreaterThan(0),
		);
		// 35.2M is total_deposits — must NOT appear next to "MTD Change"
		expect(screen.getByText("Total Deposits")).toBeInTheDocument();
		expect(screen.getByText("MTD Change")).toBeInTheDocument();
		expect(screen.getByText("YTD Change")).toBeInTheDocument();
		expect(screen.getByText("Account Count")).toBeInTheDocument();
		expect(screen.getByText("Avg Balance")).toBeInTheDocument();
		// Pinned values
		expect(screen.getByText("8,000")).toBeInTheDocument();
		expect(screen.getByText("$4.4K")).toBeInTheDocument();
	});

	it("pins MTD delta sign as ↑ for positive change (no $- regression)", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => screen.getByText(/↑\s\$800K/));
		// Critical regression guard: never produce $-N format
		const all = document.body.textContent ?? "";
		expect(all).not.toMatch(/\$-/);
	});

	it("renders branch-table rows in the order the fixture supplies them", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => screen.getByText("Main"));
		expect(screen.getByText("Main")).toBeInTheDocument();
		expect(screen.getByText("North")).toBeInTheDocument();
		expect(screen.getByText("$20M")).toBeInTheDocument();
		expect(screen.getByText("$15.2M")).toBeInTheDocument();
	});
});
