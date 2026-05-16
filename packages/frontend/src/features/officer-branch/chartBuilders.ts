import type { OfficerBranchData } from "../../shared/api/dashboardApi";
import { formatCurrency } from "../../shared/utils/format";

const PRODUCT_LABELS: Record<string, string> = {
	c_and_i: "Commercial Lending",
	cre: "Commercial Real Estate",
};

export function productLabel(slug: string): string {
	return PRODUCT_LABELS[slug] ?? slug;
}

// HUG-240: each builder treats a missing nested array (partial-mode
// payload) the same as a null data envelope — empty result, no crash.
export function buildWaterfallData(d: OfficerBranchData | null) {
	return (d?.change_by_type_waterfall ?? []).map((x) => ({
		label: productLabel(x.product),
		value: x.delta / 1_000_000,
	}));
}

export function buildSingleLoan(d: OfficerBranchData | null) {
	return (d?.single_loan_customers_by_type ?? []).map((x) => ({
		period: productLabel(x.product),
		count: x.count,
	}));
}

export function buildComboData(d: OfficerBranchData | null) {
	return (d?.combo_balance_rate ?? []).map((x) => ({
		period: productLabel(x.product),
		bar: x.balance / 1_000_000,
		line: x.weighted_avg_rate * 100,
	}));
}

export function buildBorrowerRows(
	data: OfficerBranchData | null,
): Record<string, unknown>[] {
	return (data?.top_25_borrowers ?? []).map((d) => ({
		Member: d.member_name,
		Balance: formatCurrency(d.balance),
		"Share %": `${d.share_pct.toFixed(1)}%`,
	}));
}

export function buildTabRows(
	data: OfficerBranchData | null,
): Record<string, unknown>[] {
	if (!data?.tab_data) return [];
	return data.tab_data.map((r) => ({
		Period: r.period,
		"Product Type": productLabel(r.product_type),
		Count: r.count.toLocaleString(),
		Amount: formatCurrency(r.amount),
	}));
}
