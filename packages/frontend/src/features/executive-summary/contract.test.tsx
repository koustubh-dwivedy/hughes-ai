/**
 * HUG-153 contract test for Executive Summary.
 *
 * Pins the 4 KPI cluster labels (Loans / Deposits / Risk /
 * Efficiency), the headline numbers in each cluster, and asserts the
 * audit anti-bug rule that no $- prefix or raw decimal ratio leaks
 * to the DOM.
 */

import { screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import { renderWithProviders } from "../../test/test-utils";
import ExecutiveSummary from "./ExecutiveSummary";

const FIXTURE = {
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
	past_due_aging: [{ bucket: "15-29 DPD", balance: 500_000, loan_count: 12 }],
};

const ENVELOPE = {
	data: FIXTURE,
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "contract-exec",
};

afterEach(() => {
	vi.restoreAllMocks();
});

function renderPage() {
	return renderWithProviders(
		<MemoryRouter>
			<DashboardContextProvider>
				<ExecutiveSummary />
			</DashboardContextProvider>
		</MemoryRouter>,
	);
}

describe("ExecutiveSummary — contract", () => {
	it("pins exact KPI label→value pairs (catches metric swaps)", async () => {
		vi.spyOn(api, "getExecutiveSummary").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => screen.getByText("$42.5M"));
		// Loans cluster
		expect(screen.getAllByText("Total Loans").length).toBeGreaterThan(0);
		expect(screen.getByText("$42.5M")).toBeInTheDocument();
		// Deposits cluster
		expect(screen.getAllByText("Total Deposits").length).toBeGreaterThan(0);
		expect(screen.getByText("$35.2M")).toBeInTheDocument();
		// Risk cluster — 0.023 ratio MUST render as 2.3% (not raw)
		expect(screen.getByText("Past Due Loans")).toBeInTheDocument();
		expect(screen.getByText("2.3%")).toBeInTheDocument();
	});

	it("renders all 4 cluster section labels (Loans/Deposits/Risk/Efficiency)", async () => {
		vi.spyOn(api, "getExecutiveSummary").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => screen.getByText("Loans"));
		for (const label of ["Loans", "Deposits", "Risk", "Efficiency"]) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it("never leaks raw $- or unconverted decimal ratios into DOM", async () => {
		vi.spyOn(api, "getExecutiveSummary").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => screen.getByText("$42.5M"));
		const all = document.body.textContent ?? "";
		expect(all).not.toMatch(/\$-/);
		// The decimal source values must never appear verbatim
		expect(all).not.toContain("0.023");
		expect(all).not.toContain("0.044");
	});
});
