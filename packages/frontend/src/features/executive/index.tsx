import Combo from "../../charts/Combo";
import KpiTile from "../../charts/KpiTile";
import LineTrend from "../../charts/LineTrend";
import StackedBar from "../../charts/StackedBar";
import DashboardShell from "../../layout/DashboardShell";
import { getExecutiveSummary } from "../../shared/api/api";
import type { ExecutiveSummaryData } from "../../shared/api/dashboardApi";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { useDashboard } from "../../shared/hooks/useDashboard";
import { spacing } from "../../theme/tokens";

function fmt(n: number): string {
	return `$${(n / 1_000_000).toFixed(1)}M`;
}
function pct(n: number): string {
	return `${(n * 100).toFixed(1)}%`;
}

function buildKpiTiles(data: ExecutiveSummaryData | null) {
	if (!data) return [];
	return [
		{ label: "Total Loans", value: fmt(data.total_loans_balance) },
		{ label: "Total Deposits", value: fmt(data.total_deposits_balance) },
		{ label: "MTD Loan Growth", value: fmt(data.monthly_loan_growth) },
		{ label: "YTD Loan Growth", value: fmt(data.ytd_loan_growth) },
		{ label: "MTD Deposit Growth", value: fmt(data.monthly_deposit_growth) },
		{ label: "YTD Deposit Growth", value: fmt(data.ytd_deposit_growth) },
		{ label: "Past Due Ratio", value: pct(data.blended_past_due_ratio) },
		{ label: "Loan-to-Deposit", value: pct(data.loan_to_deposit_ratio) },
		{ label: "Core Deposit Ratio", value: pct(data.core_deposit_ratio) },
	];
}

function buildLoansTrend(data: ExecutiveSummaryData | null) {
	if (!data) return [];
	return data.kpi_trend_13_months.map((d) => ({
		period: d.month,
		bar: d.total_loans_balance / 1_000_000,
		line: d.rate_spread * 100,
	}));
}

function buildMonthlyGrowth(data: ExecutiveSummaryData | null) {
	if (!data) return [];
	return [
		{ period: "Loan Growth", amount: data.monthly_loan_growth / 1_000_000 },
		{
			period: "Deposit Growth",
			amount: data.monthly_deposit_growth / 1_000_000,
		},
	];
}

export function buildAgingBar(data: ExecutiveSummaryData | null) {
	if (!data) return [];
	return data.past_due_aging.map((d) => ({
		period: d.bucket,
		balance: d.balance,
	}));
}

function buildRatioTrend(data: ExecutiveSummaryData | null) {
	if (!data) return [];
	return data.kpi_trend_13_months.map((d) => ({
		period: d.month,
		value: d.blended_past_due_ratio * 100,
	}));
}

export default function ExecutiveSummary() {
	const { asOfDate } = useDashboardContext();
	const { data, loading, error } = useDashboard(getExecutiveSummary, {
		asOfDate,
	});

	const kpiTiles = buildKpiTiles(data);
	const loansTrend = buildLoansTrend(data);
	const growthBar = buildMonthlyGrowth(data);
	const agingBar = buildAgingBar(data);
	const ratioTrend = buildRatioTrend(data);

	return (
		<DashboardShell
			title="Executive Summary"
			loading={loading}
			error={error}
			empty={!loading && !error && !data}
		>
			<div
				style={{
					display: "flex",
					gap: spacing[4],
					flexWrap: "wrap",
					marginBottom: spacing[6],
				}}
			>
				{kpiTiles.map((t) => (
					<KpiTile key={t.label} label={t.label} value={t.value} />
				))}
			</div>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: spacing[6],
					marginBottom: spacing[6],
				}}
			>
				<Combo
					data={loansTrend}
					barLabel="Loans ($M)"
					lineLabel="Rate Spread (%)"
					title="Loans & Rate Spread (13 mo.)"
					loading={loading}
				/>
				<StackedBar
					data={growthBar}
					series={[{ key: "amount" }]}
					title="MTD Growth ($M)"
					loading={loading}
				/>
			</div>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: spacing[6],
					marginBottom: spacing[6],
				}}
			>
				<StackedBar
					data={agingBar}
					series={[{ key: "balance" }]}
					title="Past Due Aging"
					loading={loading}
				/>
				<LineTrend
					data={ratioTrend}
					seriesLabel="Past Due Ratio (%)"
					title="Past Due Ratio Trend (13 mo.)"
					loading={loading}
				/>
			</div>
		</DashboardShell>
	);
}
