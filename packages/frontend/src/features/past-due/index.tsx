import DataTable from "../../charts/DataTable";
import KpiTile from "../../charts/KpiTile";
import LineTrend from "../../charts/LineTrend";
import StackedBar from "../../charts/StackedBar";
import DashboardShell from "../../layout/DashboardShell";
import { getPastDue } from "../../shared/api/api";
import type { PastDueData } from "../../shared/api/dashboardApi";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { useDashboard } from "../../shared/hooks/useDashboard";
import { spacing } from "../../theme/tokens";

function fmt(n: number): string {
	return `$${(n / 1_000_000).toFixed(1)}M`;
}

type KpiSpec = { label: string; value: string; delta?: number };

function buildKpiTiles(data: PastDueData | null): KpiSpec[] {
	if (!data) {
		return [
			{ label: "Past Due Total", value: "$0.0M" },
			{ label: "Nonaccrual", value: "$0.0M" },
			{ label: "Watchlist", value: "0" },
			{ label: "NPL Balance", value: "$0.0M" },
		];
	}
	return [
		{
			label: "Past Due Total",
			value: fmt(data.past_due_total),
			delta: -data.past_due_total_delta,
		},
		{
			label: "Nonaccrual",
			value: fmt(data.nonaccrual_total),
			delta: -data.nonaccrual_total_delta,
		},
		{
			label: "Watchlist",
			value: data.watchlist_count.toLocaleString(),
			delta: -data.watchlist_count_delta,
		},
		{
			label: "NPL Balance",
			value: fmt(data.nonperforming_balance),
			delta: -data.nonperforming_balance_delta,
		},
	];
}

export function buildDelinquencyTrend(
	data: PastDueData | null,
): { period: string; "30-59": number; "60-89": number; "90+": number }[] {
	if (!data) return [];
	return data.delinquency_trend_13_months.map((d) => ({
		period: d.month,
		"30-59": d.bucket_30_59,
		"60-89": d.bucket_60_89,
		"90+": d.bucket_90_plus,
	}));
}

function buildOfficerBarData(data: PastDueData | null) {
	if (!data) return [];
	return data.past_due_by_officer.map((d) => ({
		period: d.officer_name,
		balance: d.balance,
	}));
}

function buildRatioTrend(data: PastDueData | null) {
	if (!data) return [];
	return data.past_due_ratio_trend.map((d) => ({
		period: d.month,
		value: d.ratio,
	}));
}

function buildOfficerRows(data: PastDueData | null): Record<string, unknown>[] {
	if (!data) return [];
	return data.past_due_by_officer.map((d) => ({
		Officer: d.officer_name,
		Balance: fmt(d.balance),
		Count: d.count.toString(),
	}));
}

export default function PastDue() {
	const { asOfDate } = useDashboardContext();
	const { data, loading, error } = useDashboard(getPastDue, { asOfDate });

	const kpiTiles = buildKpiTiles(data);
	const officerBarData = buildOfficerBarData(data);
	const trendData = buildDelinquencyTrend(data);
	const ratioData = buildRatioTrend(data);
	const tableRows = buildOfficerRows(data);

	return (
		<DashboardShell
			title="Past Due"
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
					<KpiTile
						key={t.label}
						label={t.label}
						value={t.value}
						delta={t.delta}
					/>
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
				<StackedBar
					data={officerBarData}
					series={[{ key: "balance" }]}
					title="Past Due by Officer"
					loading={loading}
				/>
				<StackedBar
					data={trendData}
					series={[{ key: "30-59" }, { key: "60-89" }, { key: "90+" }]}
					title="Delinquency Trend (13 mo.)"
					loading={loading}
				/>
			</div>

			<div style={{ marginBottom: spacing[6] }}>
				<LineTrend
					data={ratioData}
					seriesLabel="Past Due Ratio"
					title="Past Due Ratio Trend"
					loading={loading}
				/>
			</div>

			<DataTable
				columns={["Officer", "Balance", "Count"]}
				rows={tableRows}
				loading={loading}
			/>
		</DashboardShell>
	);
}
