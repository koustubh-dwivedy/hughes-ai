import type {
	ExecutiveSummaryData,
	KpiTrendPoint,
} from "../../shared/api/dashboardApi";
import { formatCurrency, formatPercent } from "../../shared/utils/format";
import type { KpiTileProps } from "../../ui/primitives/KpiTile/types";

function spark(trend: KpiTrendPoint[], key: keyof KpiTrendPoint) {
	return trend.map((d) => ({ value: Number(d[key]) }));
}

function delta(n: number): string {
	if (n === 0) return "—";
	const abs = formatCurrency(Math.abs(n));
	return n > 0 ? `↑ ${abs}` : `↓ ${abs}`;
}

export function loansTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	const loanSpark = spark(d.kpi_trend_13_months, "total_loans_balance");
	return [
		{
			label: "Total Loans",
			value: formatCurrency(d.total_loans_balance),
			delta: delta(d.monthly_loan_growth),
			deltaPositive: d.monthly_loan_growth >= 0,
			sparkline: loanSpark,
			onClick: () => onTile("total_loans_balance", d.total_loans_balance),
		},
		{
			label: "MTD Loan Growth",
			value: formatCurrency(d.monthly_loan_growth),
			deltaPositive: d.monthly_loan_growth >= 0,
			onClick: () => onTile("monthly_loan_growth", d.monthly_loan_growth),
		},
		{
			label: "YTD Loan Growth",
			value: formatCurrency(d.ytd_loan_growth),
			deltaPositive: d.ytd_loan_growth >= 0,
			onClick: () => onTile("ytd_loan_growth", d.ytd_loan_growth),
		},
	];
}

export function depositsTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	const depositSpark = spark(d.kpi_trend_13_months, "total_deposits_balance");
	return [
		{
			label: "Total Deposits",
			value: formatCurrency(d.total_deposits_balance),
			delta: delta(d.monthly_deposit_growth),
			deltaPositive: d.monthly_deposit_growth >= 0,
			sparkline: depositSpark,
			onClick: () => onTile("total_deposits_balance", d.total_deposits_balance),
		},
		{
			label: "MTD Deposit Growth",
			value: formatCurrency(d.monthly_deposit_growth),
			deltaPositive: d.monthly_deposit_growth >= 0,
			onClick: () => onTile("monthly_deposit_growth", d.monthly_deposit_growth),
		},
		{
			label: "YTD Deposit Growth",
			value: formatCurrency(d.ytd_deposit_growth),
			deltaPositive: d.ytd_deposit_growth >= 0,
			onClick: () => onTile("ytd_deposit_growth", d.ytd_deposit_growth),
		},
	];
}

export function riskTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	return [
		{
			label: "Past Due Ratio",
			value: formatPercent(d.blended_past_due_ratio),
			deltaPositive: false,
			onClick: () => onTile("blended_past_due_ratio", d.blended_past_due_ratio),
		},
		{
			label: "Loan-to-Deposit",
			value: formatPercent(d.loan_to_deposit_ratio),
			onClick: () => onTile("loan_to_deposit_ratio", d.loan_to_deposit_ratio),
		},
	];
}

export function efficiencyTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	return [
		{
			label: "Core Deposit Ratio",
			value: formatPercent(d.core_deposit_ratio),
			deltaPositive: d.core_deposit_ratio >= 0.5,
			onClick: () => onTile("core_deposit_ratio", d.core_deposit_ratio),
		},
	];
}
