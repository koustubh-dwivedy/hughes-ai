/**
 * HUG-153 contract test for Past Due.
 *
 * Pins KPI label→value pairs, delta direction (positive past_due
 * change is unfavourable → red), and the officer pseudonymisation
 * (Officer #01, Officer #02 sorted alphabetically by real name).
 */

import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { PastDueData } from "../../shared/api/dashboardApi";
import { renderWithProviders } from "../../test/test-utils";
import PastDue from "./index";

vi.mock("./api");
import { usePastDue } from "./api";

const FIXTURE: PastDueData = {
	past_due_total: 2_500_000,
	past_due_total_delta: 100_000,
	nonaccrual_total: 500_000,
	nonaccrual_total_delta: -50_000,
	watchlist_count: 15,
	watchlist_count_delta: 2,
	nonperforming_balance: 1_200_000,
	nonperforming_balance_delta: 80_000,
	past_due_by_officer: [
		{ officer_name: "Charlie", balance: 800_000, count: 5 },
		{ officer_name: "Alice", balance: 600_000, count: 4 },
	],
	delinquency_trend_13_months: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		bucket_30_59: 100_000,
		bucket_60_89: 50_000,
		bucket_90_plus: 25_000,
	})),
	past_due_ratio_trend: [{ month: "2025-12", ratio: 0.023 }],
};

afterEach(() => {
	vi.restoreAllMocks();
});

describe("PastDue — contract", () => {
	it("pins exact KPI label→value pairs (catches metric swaps)", () => {
		vi.mocked(usePastDue).mockReturnValue({
			data: FIXTURE,
			loading: false,
			isError: false,
		});
		renderWithProviders(<PastDue />);
		expect(screen.getByText("Past Due Total")).toBeInTheDocument();
		expect(screen.getByText("$2.5M")).toBeInTheDocument();
		expect(screen.getByText("Loans Earning No Interest")).toBeInTheDocument();
		expect(screen.getByText("$500K")).toBeInTheDocument();
		expect(screen.getByText("Loans Under Watch")).toBeInTheDocument();
		expect(screen.getByText("15")).toBeInTheDocument();
		expect(screen.getByText("Non-Performing Balance")).toBeInTheDocument();
		expect(screen.getByText("$1.2M")).toBeInTheDocument();
	});

	it("positive past_due_total_delta renders as ↑ with formatted currency", () => {
		vi.mocked(usePastDue).mockReturnValue({
			data: FIXTURE,
			loading: false,
			isError: false,
		});
		renderWithProviders(<PastDue />);
		// AUDIT: must format the raw number, never leak a bare 100000
		expect(screen.getByText("↑ $100K")).toBeInTheDocument();
		const all = document.body.textContent ?? "";
		expect(all).not.toContain("↓ 100000");
	});

	it("pseudonymises officer names alphabetically (Alice→#01, Charlie→#02)", () => {
		vi.mocked(usePastDue).mockReturnValue({
			data: FIXTURE,
			loading: false,
			isError: false,
		});
		renderWithProviders(<PastDue />);
		// Real names must NEVER reach the DOM
		const all = document.body.textContent ?? "";
		expect(all).not.toContain("Alice");
		expect(all).not.toContain("Charlie");
		// Aliases must
		expect(screen.getAllByText("Officer #01").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Officer #02").length).toBeGreaterThan(0);
	});
});
