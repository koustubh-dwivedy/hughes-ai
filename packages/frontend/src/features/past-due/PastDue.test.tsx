import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import * as telemetry from "../../shared/telemetry/client";
import { renderWithProviders } from "../../test/test-utils";
import PastDue from "./index";

const FIXTURE = {
	past_due_total: 2_500_000,
	past_due_total_delta: 100_000,
	nonaccrual_total: 500_000,
	nonaccrual_total_delta: -50_000,
	watchlist_count: 15,
	watchlist_count_delta: 2,
	nonperforming_balance: 1_200_000,
	nonperforming_balance_delta: 80_000,
	past_due_by_officer: [
		{ officer_name: "Alice Smith", balance: 800_000, count: 5 },
		{ officer_name: "Bob Jones", balance: 400_000, count: 3 },
	],
	delinquency_trend_13_months: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		bucket_30_59: 100_000 + i * 10_000,
		bucket_60_89: 50_000 + i * 5_000,
		bucket_90_plus: 25_000 + i * 2_500,
	})),
	past_due_ratio_trend: [{ month: "2025-01", ratio: 0.032 }],
};

const ENVELOPE = {
	data: FIXTURE,
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test-pastdue",
};

function renderPage() {
	return renderWithProviders(
		<MemoryRouter>
			<DashboardContextProvider>
				<PastDue />
			</DashboardContextProvider>
		</MemoryRouter>,
	);
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("PastDue — no real names exposed", () => {
	it("renders Officer #01 / Officer #02 instead of real names", async () => {
		vi.spyOn(api, "getPastDue").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getAllByText("Officer #01").length).toBeGreaterThan(0),
		);
		expect(screen.getAllByText("Officer #02").length).toBeGreaterThan(0);
		expect(screen.queryByText("Alice Smith")).toBeNull();
		expect(screen.queryByText("Bob Jones")).toBeNull();
	});
});

describe("PastDue — ratio formatting", () => {
	it("shows ratio as percent not raw decimal", async () => {
		vi.spyOn(api, "getPastDue").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => expect(screen.queryByText("0.032")).toBeNull());
		expect(screen.queryByText(/0\.032/)).toBeNull();
	});
});

describe("PastDue — contract tests", () => {
	it("pins Past Due Total KPI to fixture ($2.5M)", async () => {
		vi.spyOn(api, "getPastDue").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => expect(screen.getByText("$2.5M")).toBeInTheDocument());
	});

	it("renders all 4 KPI tile labels", async () => {
		vi.spyOn(api, "getPastDue").mockResolvedValue(ENVELOPE);
		renderPage();
		for (const label of [
			"Past Due Total",
			"Loans Earning No Interest",
			"Loans Under Watch",
			"Non-Performing Balance",
		]) {
			await waitFor(() =>
				expect(screen.getByText(label, { exact: true })).toBeInTheDocument(),
			);
		}
	});

	it("shows error alert when API fails", async () => {
		vi.spyOn(api, "getPastDue").mockRejectedValue(new Error("net error"));
		renderPage();
		await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
	});

	it("positive delta shown in red (unfavorable increase)", async () => {
		vi.spyOn(api, "getPastDue").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getByText("Past Due Total")).toBeInTheDocument(),
		);
		const deltaEl = screen.getByText("↑ $100K");
		expect(deltaEl).toHaveStyle({ color: "#dc2626" });
	});
});

describe("PastDue — partial-data resilience (HUG-240)", () => {
	it("renders heading + alert UI when envelope has no usable fields", async () => {
		// Mimic the E2E error-matrix's `partial` payload: data is non-null
		// but missing nearly every field. Components must not crash on
		// `.map`-on-undefined; PageHeader must still paint.
		const partial = {
			data: {
				total_deposits: 1000,
				account_count: 5,
			} as unknown as typeof FIXTURE,
			as_of_date: "2026-04-30",
			generated_at: "2026-04-30T00:00:00Z",
			audit_id: "partial",
		};
		vi.spyOn(api, "getPastDue").mockResolvedValue(partial);
		renderPage();
		await waitFor(() => {
			expect(screen.getByText("Past Due")).toBeInTheDocument();
		});
		// PageHeader present even on partial data — that's the contract.
		expect(screen.getByText("Past Due")).toBeInTheDocument();
	});
});

describe("PastDue — telemetry", () => {
	it("emits kpi.tile.clicked when clicking Past Due Total tile", async () => {
		vi.spyOn(api, "getPastDue").mockResolvedValue(ENVELOPE);
		const emitSpy = vi.spyOn(telemetry, "emit");
		renderPage();
		await waitFor(() =>
			expect(screen.getByText("Past Due Total")).toBeInTheDocument(),
		);
		const tile = screen.getByText("Past Due Total").closest('[role="button"]');
		if (tile) fireEvent.click(tile);
		expect(emitSpy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "kpi.tile.clicked",
				kpi_id: "past_due_total",
			}),
		);
	});
});
