import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import * as telemetry from "../../shared/telemetry/client";
import { renderWithProviders } from "../../test/test-utils";
import DepositPortfolio from "./DepositPortfolio";

const FIXTURE = {
	total_deposits: 35_200_000,
	mtd_change: 800_000,
	ytd_change: 3_100_000,
	avg_balance_per_customer: 4_400,
	account_count: 8_000,
	top_25_deposits: [],
	deposits_by_branch: [
		{ branch_name: "Main Branch", balance: 20_000_000 },
		{ branch_name: "East Branch", balance: 15_200_000 },
	],
	deposit_mix: [
		{ product: "Savings", balance: 18_000_000, share_pct: 0.51 },
		{ product: "Checking", balance: 10_000_000, share_pct: 0.28 },
		{ product: "CDs", balance: 5_000_000, share_pct: 0.14 },
		{ product: "Money Market", balance: 2_200_000, share_pct: 0.06 },
	],
	change_by_product: [
		{ product: "Savings", delta: 500_000 },
		{ product: "Checking", delta: -100_000 },
		{ product: "CDs", delta: 400_000 },
	],
	new_vs_closed_accounts: {
		opened: { count: 120, amount: 2_400_000 },
		closed: { count: 35, amount: 700_000 },
	},
};

const ENVELOPE = {
	data: FIXTURE,
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test-deposits",
};

function renderPage() {
	return renderWithProviders(
		<MemoryRouter>
			<DashboardContextProvider>
				<DepositPortfolio />
			</DashboardContextProvider>
		</MemoryRouter>,
	);
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("DepositPortfolio — contract tests", () => {
	it("renders all KPI tile labels", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		for (const label of [
			"Total Deposits",
			"MTD Change",
			"YTD Change",
			"Account Count",
			"Avg Balance",
			"New Accounts",
			"Closed Accounts",
		]) {
			await waitFor(() =>
				expect(screen.getByText(label, { exact: true })).toBeInTheDocument(),
			);
		}
	});

	it("pins Total Deposits value to fixture ($35.2M)", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getAllByText("$35.2M").length).toBeGreaterThan(0),
		);
	});

	it("pins Account Count to fixture (8,000)", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => expect(screen.getByText("8,000")).toBeInTheDocument());
	});

	it("formats negative MTD change correctly (↓ not $-)", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue({
			...ENVELOPE,
			data: { ...FIXTURE, mtd_change: -237_659.38 },
		});
		renderPage();
		await waitFor(() => expect(screen.queryByText(/\$-/)).toBeNull());
		expect(screen.queryByText(/237659\.38/)).toBeNull();
	});

	it("shows page header with Deposit Portfolio title", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(
				screen.getByRole("heading", { name: "Deposit Portfolio" }),
			).toBeInTheDocument(),
		);
	});

	it("groups top 3 deposit mix slices and collapses remainder to Other", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getAllByText("Savings").length).toBeGreaterThan(0),
		);
		expect(screen.getAllByText("Other").length).toBeGreaterThan(0);
		expect(screen.queryByText("Money Market")).toBeNull();
	});

	it("renders branch table rows", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getByText("Main Branch")).toBeInTheDocument(),
		);
		expect(screen.getByText("East Branch")).toBeInTheDocument();
	});

	it("shows error alert when API fails", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockRejectedValue(
			new Error("network error"),
		);
		renderPage();
		await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
	});

	it("shows New Accounts and Closed Accounts tiles", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() => expect(screen.getByText("120")).toBeInTheDocument());
		expect(screen.getByText("35")).toBeInTheDocument();
	});
});

describe("DepositPortfolio — telemetry", () => {
	it("emits kpi.tile.clicked when clicking Total Deposits tile", async () => {
		vi.spyOn(api, "getDepositPortfolio").mockResolvedValue(ENVELOPE);
		const emitSpy = vi.spyOn(telemetry, "emit");
		renderPage();
		await waitFor(() =>
			expect(screen.getByText("Total Deposits")).toBeInTheDocument(),
		);
		const tile = screen.getByText("Total Deposits").closest('[role="button"]');
		if (tile) fireEvent.click(tile);
		expect(emitSpy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "kpi.tile.clicked",
				kpi_id: "total_deposits",
			}),
		);
	});
});
