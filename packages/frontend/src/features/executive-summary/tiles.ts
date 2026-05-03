import type { ExecutiveSummaryData } from "../../shared/api/dashboardApi";
import { metricDef } from "../../shared/insights/glossary";
import { formatCurrency, formatPercent } from "../../shared/utils/format";
import type { KpiTileProps } from "../../ui/primitives/KpiTile/types";

function delta(n: number): string {
	if (n === 0) return "—";
	const abs = formatCurrency(Math.abs(n));
	return n > 0 ? `↑ ${abs}` : `↓ ${abs}`;
}

function tileBase(id: string, fallbackLabel: string) {
	const def = metricDef(id);
	return {
		label: def?.short ?? fallbackLabel,
		infoTooltip: def?.tooltip,
	};
}

export function loansTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	return [
		{
			...tileBase("total_loans", "Total Loans"),
			value: formatCurrency(d.total_loans_balance),
			delta: delta(d.monthly_loan_growth),
			deltaLabel: "MoM",
			deltaPositive: d.monthly_loan_growth >= 0,
			onClick: () => onTile("total_loans_balance", d.total_loans_balance),
		},
		{
			...tileBase("mtd_loan_growth", "MTD Loan Growth"),
			value: formatCurrency(d.monthly_loan_growth),
			deltaLabel: "this month",
			deltaPositive: d.monthly_loan_growth >= 0,
			onClick: () => onTile("monthly_loan_growth", d.monthly_loan_growth),
		},
		{
			...tileBase("ytd_loan_growth", "YTD Loan Growth"),
			value: formatCurrency(d.ytd_loan_growth),
			deltaLabel: "since Jan 1",
			deltaPositive: d.ytd_loan_growth >= 0,
			onClick: () => onTile("ytd_loan_growth", d.ytd_loan_growth),
		},
	];
}

export function depositsTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	return [
		{
			...tileBase("total_deposits", "Total Deposits"),
			value: formatCurrency(d.total_deposits_balance),
			delta: delta(d.monthly_deposit_growth),
			deltaLabel: "MoM",
			deltaPositive: d.monthly_deposit_growth >= 0,
			onClick: () => onTile("total_deposits_balance", d.total_deposits_balance),
		},
		{
			...tileBase("mtd_deposit_growth", "MTD Deposit Growth"),
			value: formatCurrency(d.monthly_deposit_growth),
			deltaLabel: "this month",
			deltaPositive: d.monthly_deposit_growth >= 0,
			onClick: () => onTile("monthly_deposit_growth", d.monthly_deposit_growth),
		},
		{
			...tileBase("ytd_deposit_growth", "YTD Deposit Growth"),
			value: formatCurrency(d.ytd_deposit_growth),
			deltaLabel: "since Jan 1",
			deltaPositive: d.ytd_deposit_growth >= 0,
			onClick: () => onTile("ytd_deposit_growth", d.ytd_deposit_growth),
		},
	];
}

export function riskTiles(
	d: ExecutiveSummaryData,
	onTile: (id: string, value: number) => void,
): KpiTileProps[] {
	const ratioPct = d.blended_past_due_ratio * 100;
	return [
		{
			...tileBase("past_due_ratio", "Past Due Ratio"),
			value: formatPercent(d.blended_past_due_ratio),
			context:
				ratioPct < 1.5
					? "Within healthy band (<1.5%)"
					: ratioPct < 2.5
						? "Above healthy band — monitor"
						: "Elevated — investigate",
			deltaPositive: ratioPct < 1.5,
			onClick: () => onTile("blended_past_due_ratio", d.blended_past_due_ratio),
		},
		{
			...tileBase("loan_to_deposit", "Loan-to-Deposit"),
			value: formatPercent(d.loan_to_deposit_ratio),
			context:
				d.loan_to_deposit_ratio > 0.9
					? "High utilization — limited liquidity headroom"
					: d.loan_to_deposit_ratio < 0.6
						? "Low utilization — under-deployed deposits"
						: "Within typical CU range (60–90%)",
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
			...tileBase("core_deposit_ratio", "Core Deposit Ratio"),
			value: formatPercent(d.core_deposit_ratio),
			context:
				d.core_deposit_ratio >= 0.5
					? "Healthy: half-plus of deposits are sticky"
					: "Heavy CD/MM mix — funding cost more rate-sensitive",
			deltaPositive: d.core_deposit_ratio >= 0.5,
			onClick: () => onTile("core_deposit_ratio", d.core_deposit_ratio),
		},
	];
}
