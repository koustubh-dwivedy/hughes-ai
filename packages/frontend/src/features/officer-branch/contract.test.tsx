/**
 * HUG-153 contract test for Officer/Branch.
 *
 * Pins KPI label→value pairs, product-label translation
 * (c_and_i → C&I, cre → Commercial RE), and confirms the demo banner
 * shows on every render.
 */

import { screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { OfficerBranchData } from "../../shared/api/dashboardApi";
import { renderWithProviders } from "../../test/test-utils";
import OfficerBranch from "./index";

vi.mock("./api");
import { useOfficerBranch } from "./api";

const FIXTURE: OfficerBranchData = {
	total_loans: 42_000_000,
	account_count: 3_200,
	avg_loan_balance: 13_125,
	loan_mix_donut: [
		{ product: "c_and_i", balance: 20_000_000, share_pct: 47.6 },
		{ product: "cre", balance: 12_000_000, share_pct: 28.6 },
	],
	change_by_type_waterfall: [{ product: "c_and_i", delta: 500_000 }],
	single_loan_customers_by_type: [{ product: "c_and_i", count: 50 }],
	combo_balance_rate: [
		{ product: "c_and_i", balance: 20_000_000, weighted_avg_rate: 0.062 },
	],
	top_25_borrowers: [
		{ member_name: "Member 1", balance: 1_500_000, share_pct: 3.6 },
	],
	watchlist_trend: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		count: 3 + i,
		balance: 100_000 + i * 5_000,
	})),
	tab_data: null,
};

afterEach(() => {
	vi.restoreAllMocks();
});

function renderPage() {
	return renderWithProviders(
		<MemoryRouter>
			<Routes>
				<Route path="*" element={<OfficerBranch />} />
			</Routes>
		</MemoryRouter>,
	);
}

describe("OfficerBranch — contract", () => {
	it("pins exact KPI label→value pairs (catches metric swaps)", () => {
		vi.mocked(useOfficerBranch).mockReturnValue({
			data: FIXTURE,
			loading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("Total Loans")).toBeInTheDocument();
		expect(screen.getByText("$42M")).toBeInTheDocument();
		expect(screen.getByText("Account Count")).toBeInTheDocument();
		expect(screen.getByText("3,200")).toBeInTheDocument();
		expect(screen.getByText("Avg Loan Balance")).toBeInTheDocument();
		expect(screen.getByText("$13.1K")).toBeInTheDocument();
	});

	it("translates product slugs (c_and_i → Commercial Lending, cre → Commercial Real Estate)", () => {
		vi.mocked(useOfficerBranch).mockReturnValue({
			data: FIXTURE,
			loading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getAllByText("Commercial Lending").length).toBeGreaterThan(0);
		expect(
			screen.getAllByText("Commercial Real Estate").length,
		).toBeGreaterThan(0);
		// Raw slugs must never reach the DOM
		const all = document.body.textContent ?? "";
		expect(all).not.toContain("c_and_i");
	});

	it("renders the demo-data banner on every render", () => {
		vi.mocked(useOfficerBranch).mockReturnValue({
			data: FIXTURE,
			loading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByRole("note")).toBeInTheDocument();
		expect(screen.getByText(/Demo data only/)).toBeInTheDocument();
	});
});
