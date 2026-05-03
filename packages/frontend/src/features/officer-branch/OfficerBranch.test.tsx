import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import * as telemetry from "../../shared/telemetry/client";
import { renderWithProviders } from "../../test/test-utils";
import OfficerBranch from "./index";

const FIXTURE = {
	total_loans: 15_000_000,
	account_count: 800,
	avg_loan_balance: 18_750,
	loan_mix_donut: [{ product: "Auto", balance: 8_000_000, share_pct: 53 }],
	change_by_type_waterfall: [{ product: "Auto", delta: 200_000 }],
	single_loan_customers_by_type: [{ product: "Auto", count: 120 }],
	combo_balance_rate: [
		{ product: "Auto", balance: 8_000_000, weighted_avg_rate: 0.06 },
	],
	top_25_borrowers: [
		{ member_name: "Member 1", balance: 500_000, share_pct: 3.3 },
	],
	watchlist_trend: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		count: 3 + i,
		balance: 100_000 + i * 5_000,
	})),
	tab_data: null,
};

const ENVELOPE = {
	data: FIXTURE,
	as_of_date: "2025-12-31",
	generated_at: "2026-04-30T00:00:00Z",
	audit_id: "test-officer",
};

function renderPage(initialEntries: string[] = ["/"]) {
	return renderWithProviders(
		<MemoryRouter initialEntries={initialEntries}>
			<Routes>
				<Route
					path="*"
					element={
						<DashboardContextProvider>
							<OfficerBranch />
						</DashboardContextProvider>
					}
				/>
			</Routes>
		</MemoryRouter>,
	);
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("OfficerBranch — product labels", () => {
	it("maps c_and_i slug to Commercial Lending in loan mix", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue({
			...ENVELOPE,
			data: {
				...FIXTURE,
				loan_mix_donut: [
					{ product: "c_and_i", balance: 8_000_000, share_pct: 53 },
				],
			},
		});
		renderPage();
		await waitFor(() =>
			expect(screen.getAllByText("Commercial Lending").length).toBeGreaterThan(
				0,
			),
		);
	});

	it("maps cre slug to Commercial Real Estate", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue({
			...ENVELOPE,
			data: {
				...FIXTURE,
				loan_mix_donut: [{ product: "cre", balance: 5_000_000, share_pct: 33 }],
			},
		});
		renderPage();
		await waitFor(() =>
			expect(
				screen.getAllByText("Commercial Real Estate").length,
			).toBeGreaterThan(0),
		);
	});
});

describe("OfficerBranch — filter dropdowns", () => {
	it("branch filter renders with All Branches default", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getByLabelText("Branch filter")).toBeInTheDocument(),
		);
		const select = screen.getByLabelText("Branch filter") as HTMLSelectElement;
		expect(select.value).toBe("");
	});

	it("officer filter renders with All Officers default", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENVELOPE);
		renderPage();
		await waitFor(() =>
			expect(screen.getByLabelText("Officer filter")).toBeInTheDocument(),
		);
		const select = screen.getByLabelText("Officer filter") as HTMLSelectElement;
		expect(select.value).toBe("");
	});
});

describe("OfficerBranch — telemetry", () => {
	it("emits tab.switched when switching tabs", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENVELOPE);
		const emitSpy = vi.spyOn(telemetry, "emit");
		renderPage();
		await waitFor(() =>
			expect(screen.getByRole("tab", { name: "Renewed" })).toBeInTheDocument(),
		);
		fireEvent.click(screen.getByRole("tab", { name: "Renewed" }));
		expect(emitSpy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "tab.switched",
				tab_id: "renewed",
				panel_id: "officer-branch",
			}),
		);
	});

	it("emits filter.changed when changing branch filter", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENVELOPE);
		const emitSpy = vi.spyOn(telemetry, "emit");
		renderPage();
		await waitFor(() =>
			expect(screen.getByLabelText("Branch filter")).toBeInTheDocument(),
		);
		fireEvent.change(screen.getByLabelText("Branch filter"), {
			target: { value: "1" },
		});
		expect(emitSpy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "filter.changed",
				filter_name: "branch_id",
				value: "1",
			}),
		);
	});

	it("emits filter.changed when changing officer filter", async () => {
		vi.spyOn(api, "getOfficerBranch").mockResolvedValue(ENVELOPE);
		const emitSpy = vi.spyOn(telemetry, "emit");
		renderPage();
		await waitFor(() =>
			expect(screen.getByLabelText("Officer filter")).toBeInTheDocument(),
		);
		fireEvent.change(screen.getByLabelText("Officer filter"), {
			target: { value: "off-02" },
		});
		expect(emitSpy).toHaveBeenCalledWith(
			expect.objectContaining({
				type: "filter.changed",
				filter_name: "officer_id",
				value: "off-02",
			}),
		);
	});
});
