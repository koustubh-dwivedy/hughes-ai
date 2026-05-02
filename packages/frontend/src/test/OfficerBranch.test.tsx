import { fireEvent, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import OfficerBranch, {
	buildBorrowerRows,
	buildLoanMix,
	buildTabRows,
} from "../features/officer-branch";
import type { OfficerBranchData } from "../shared/api/dashboardApi";
import { renderWithProviders } from "./test-utils";

vi.mock("../features/officer-branch/api");
import { useOfficerBranch } from "../features/officer-branch/api";

const PRODUCTS = [
	"Auto",
	"Mortgage",
	"Personal",
	"HELOC",
	"Business",
	"Student",
	"RV",
	"Boat",
];

const fixture: OfficerBranchData = {
	total_loans: 42_000_000,
	account_count: 3_200,
	avg_loan_balance: 13_125,
	loan_mix_donut: PRODUCTS.map((p, i) => ({
		product: p,
		balance: 5_000_000 + i * 500_000,
		share_pct: 12.5,
	})),
	change_by_type_waterfall: PRODUCTS.map((p, i) => ({
		product: p,
		delta: (i % 2 === 0 ? 1 : -1) * 200_000,
	})),
	single_loan_customers_by_type: PRODUCTS.map((p, i) => ({
		product: p,
		count: 100 + i * 20,
	})),
	combo_balance_rate: PRODUCTS.map((p, i) => ({
		product: p,
		balance: 5_000_000 + i * 500_000,
		weighted_avg_rate: 0.05 + i * 0.005,
	})),
	top_25_borrowers: Array.from({ length: 25 }, (_, i) => ({
		member_name: `Member ${i + 1}`,
		balance: 1_000_000 - i * 30_000,
		share_pct: 2.4 - i * 0.09,
	})),
	watchlist_trend: Array.from({ length: 13 }, (_, i) => ({
		month: `2025-${String(i + 1).padStart(2, "0")}`,
		count: 3 + i,
		balance: 100_000 + i * 10_000,
	})),
	tab_data: null,
};

interface MockShape {
	data?: OfficerBranchData | null;
	loading?: boolean;
	isError?: boolean;
}
function mockHook(overrides: MockShape) {
	vi.mocked(useOfficerBranch).mockReturnValue({
		data: null,
		loading: false,
		isError: false,
		...overrides,
	});
}

function renderInRouter(initialEntries: string[] = ["/"]) {
	return renderWithProviders(
		<MemoryRouter initialEntries={initialEntries}>
			<Routes>
				<Route path="*" element={<OfficerBranch />} />
			</Routes>
		</MemoryRouter>,
	);
}

describe("OfficerBranch", () => {
	it("renders Demo data only banner and KPI tiles", () => {
		mockHook({ data: fixture });
		renderInRouter();
		expect(screen.getByRole("note")).toBeInTheDocument();
		expect(screen.getByText(/Demo data only/i)).toBeInTheDocument();
		expect(screen.getByText("Total Loans")).toBeInTheDocument();
		expect(screen.getByText("$42M")).toBeInTheDocument();
	});

	it("buildLoanMix maps 8 products to donut slices", () => {
		const result = buildLoanMix(fixture);
		expect(result).toHaveLength(8);
		expect(result[0]).toMatchObject({
			label: "Auto",
			value: expect.any(Number),
		});
	});

	it("buildBorrowerRows maps 25 borrowers to table rows", () => {
		const result = buildBorrowerRows(fixture);
		expect(result).toHaveLength(25);
		expect(result[0]).toMatchObject({ Member: "Member 1" });
	});

	it("tab switching changes URL and refetches", () => {
		mockHook({ data: fixture });
		renderInRouter();

		const newTab = screen.getByRole("tab", { name: "New" });
		fireEvent.click(newTab);

		expect(newTab).toHaveAttribute("aria-selected", "true");
		const calls = vi.mocked(useOfficerBranch).mock.calls;
		expect(calls[calls.length - 1]?.[0]).toMatchObject({ tab: "new" });
	});

	it("deep-link ?tab=paid_off activates Paid Off tab", () => {
		mockHook({ data: fixture });
		renderInRouter(["/?tab=paid_off"]);

		expect(screen.getByRole("tab", { name: "Paid Off" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByRole("tab", { name: "New" })).toHaveAttribute(
			"aria-selected",
			"false",
		);
	});

	it("watchlist trend renders 13-month figure", () => {
		mockHook({ data: fixture });
		renderInRouter();
		expect(
			screen.getByRole("figure", { name: "Watchlist Trend (13 mo.)" }),
		).toBeInTheDocument();
	});

	it("buildTabRows maps tab_data rows", () => {
		const withTab: OfficerBranchData = {
			...fixture,
			tab_data: [
				{ period: "2025-01", product_type: "Auto", count: 5, amount: 250_000 },
			],
		};
		const rows = buildTabRows(withTab);
		expect(rows).toHaveLength(1);
		expect(rows[0]).toMatchObject({
			Period: "2025-01",
			"Product Type": "Auto",
			Count: "5",
		});
	});
});
