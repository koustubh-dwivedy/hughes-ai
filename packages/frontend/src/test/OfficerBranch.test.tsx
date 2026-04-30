import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import OfficerBranch, {
	buildBorrowerRows,
	buildLoanMix,
} from "../dashboards/OfficerBranch";
import type { UseDashboardResult } from "../hooks/useDashboard";
import type { OfficerBranchData } from "../lib/dashboardApi";

vi.mock("../hooks/useDashboard");
import { useDashboard } from "../hooks/useDashboard";

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
};

function mockHook(overrides: Partial<UseDashboardResult<OfficerBranchData>>) {
	vi.mocked(useDashboard).mockReturnValue({
		data: null,
		loading: false,
		error: null,
		refetch: vi.fn(),
		...overrides,
	});
}

describe("OfficerBranch", () => {
	it("renders Demo data only banner and KPI tiles", () => {
		mockHook({ data: fixture });
		render(<OfficerBranch />);
		expect(screen.getByRole("note")).toBeInTheDocument();
		expect(screen.getByText(/Demo data only/i)).toBeInTheDocument();
		expect(screen.getByText("Total Loans")).toBeInTheDocument();
		expect(screen.getByText("$42.0M")).toBeInTheDocument();
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
});
