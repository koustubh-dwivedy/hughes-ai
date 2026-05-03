import LineTrend from "../../charts/LineTrend";
import StackedBar from "../../charts/StackedBar";
import type {
	OfficerDelinquency,
	PastDueData,
} from "../../shared/api/dashboardApi";
import DashboardHeadline from "../../shared/components/DashboardHeadline";
import InsightCard from "../../shared/components/InsightCard";
import MonthSelector from "../../shared/components/MonthSelector";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { metricDef } from "../../shared/insights/glossary";
import { pastDueHeadline } from "../../shared/insights/headlines";
import {
	officerLoadInsight,
	pastDueTrendInsight,
	ratioTrendInsight,
} from "../../shared/insights/rules";
import { emit } from "../../shared/telemetry/client";
import { formatCurrency, formatPercent } from "../../shared/utils/format";
import { spacing } from "../../theme/tokens";
import ChartCard from "../../ui/primitives/ChartCard";
import DataTable from "../../ui/primitives/DataTable";
import KpiTile from "../../ui/primitives/KpiTile";
import PageHeader from "../../ui/primitives/PageHeader";
import { usePastDue } from "./api";

const LOADING_KEYS = ["a", "b", "c", "d"];

const SEVERITY_SERIES = [
	{ key: "30-59", color: "#f59e0b" },
	{ key: "60-89", color: "#f97316" },
	{ key: "90+", color: "#ef4444" },
];

const tilesRowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
	gap: spacing[4],
	marginBottom: spacing[6],
};

const gridStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
	gap: spacing[6],
	marginBottom: spacing[6],
};

function pseudonymMap(officers: OfficerDelinquency[]): Map<string, string> {
	const names = [...officers].map((o) => o.officer_name).sort();
	return new Map(
		names.map((name, i) => [
			name,
			`Officer #${String(i + 1).padStart(2, "0")}`,
		]),
	);
}

export function buildDelinquencyTrend(data: PastDueData | null) {
	if (!data) return [];
	return data.delinquency_trend_13_months.map((d) => ({
		period: d.month,
		"30-59": d.bucket_30_59,
		"60-89": d.bucket_60_89,
		"90+": d.bucket_90_plus,
	}));
}

function onTile(kpi_id: string, value: number) {
	emit({ type: "kpi.tile.clicked", kpi_id, value });
}

function tileFromDef(id: string, fallbackLabel: string) {
	const def = metricDef(id);
	return {
		label: def?.short ?? fallbackLabel,
		infoTooltip: def?.tooltip,
	};
}

function buildKpiTiles(d: PastDueData) {
	return [
		{
			id: "past_due_total",
			...tileFromDef("past_due_total", "Past Due Total"),
			value: formatCurrency(d.past_due_total),
			delta:
				d.past_due_total_delta > 0
					? `↑ ${formatCurrency(d.past_due_total_delta)}`
					: `↓ ${formatCurrency(Math.abs(d.past_due_total_delta))}`,
			deltaPositive: d.past_due_total_delta <= 0,
			onClick: () => onTile("past_due_total", d.past_due_total),
		},
		{
			id: "nonaccrual_total",
			...tileFromDef("nonaccrual_total", "Nonaccrual"),
			value: formatCurrency(d.nonaccrual_total),
			deltaPositive: d.nonaccrual_total_delta <= 0,
			onClick: () => onTile("nonaccrual_total", d.nonaccrual_total),
		},
		{
			id: "watchlist_count",
			...tileFromDef("watchlist_count", "Watchlist"),
			value: d.watchlist_count.toLocaleString(),
			deltaPositive: d.watchlist_count_delta <= 0,
			onClick: () => onTile("watchlist_count", d.watchlist_count),
		},
		{
			id: "nonperforming_balance",
			...tileFromDef("nonperforming_balance", "NPL Balance"),
			value: formatCurrency(d.nonperforming_balance),
			deltaPositive: d.nonperforming_balance_delta <= 0,
			onClick: () => onTile("nonperforming_balance", d.nonperforming_balance),
		},
	];
}

// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: dashboard render — conditional sections (loading/error) are intrinsic
export default function PastDue() {
	const { asOfDate } = useDashboardContext();
	const { data, loading, isError } = usePastDue({ asOfDate });

	if (isError)
		return (
			<div>
				<PageHeader title="Past Due" eyebrow="Credit Risk" />
				<p role="alert">Failed to load past due data.</p>
			</div>
		);

	const aliases = data
		? pseudonymMap(data.past_due_by_officer)
		: new Map<string, string>();
	const kpiTiles = data ? buildKpiTiles(data) : [];
	const trendData = buildDelinquencyTrend(data);
	const ratioData = data
		? data.past_due_ratio_trend.map((d) => ({
				period: d.month,
				value: d.ratio * 100,
			}))
		: [];
	const officerBarData = data
		? data.past_due_by_officer.map((d) => ({
				period: aliases.get(d.officer_name) ?? d.officer_name,
				balance: d.balance,
			}))
		: [];
	const tableRows = data
		? data.past_due_by_officer.map((d) => ({
				Officer: aliases.get(d.officer_name) ?? d.officer_name,
				Balance: formatCurrency(d.balance),
				Count: d.count.toString(),
				Ratio: formatPercent(d.balance / (data.past_due_total || 1)),
			}))
		: [];

	return (
		<div>
			<PageHeader
				title="Past Due"
				eyebrow="Credit Risk"
				actions={<MonthSelector surface="past-due" />}
			/>
			{data && <DashboardHeadline headline={pastDueHeadline(data)} />}

			<div style={tilesRowStyle}>
				{loading
					? LOADING_KEYS.map((k) => (
							<KpiTile key={k} label="" value="" loading />
						))
					: kpiTiles.map(({ id: _id, ...props }) => (
							<KpiTile key={props.label} {...props} />
						))}
			</div>

			<div style={gridStyle}>
				<ChartCard
					title="Past-Due Balance by Officer"
					subtitle="Who carries the most overdue book this month"
					loading={loading}
					footer={
						!loading && <InsightCard {...officerLoadInsight(officerBarData)} />
					}
				>
					<StackedBar
						data={officerBarData}
						series={[{ key: "balance" }]}
						loading={loading}
					/>
				</ChartCard>
				<ChartCard
					title="Delinquency by Lateness Bucket (13 mo.)"
					subtitle="30-59 / 60-89 / 90+ days past due"
					loading={loading}
					footer={
						!loading && <InsightCard {...pastDueTrendInsight(trendData)} />
					}
				>
					<StackedBar
						data={trendData}
						series={SEVERITY_SERIES}
						loading={loading}
					/>
				</ChartCard>
			</div>

			<ChartCard
				title="Past-Due Ratio (%)"
				subtitle="Share of loan balance 30+ days late"
				loading={loading}
				footer={!loading && <InsightCard {...ratioTrendInsight(ratioData)} />}
			>
				<LineTrend
					data={ratioData}
					seriesLabel="Past Due Ratio (%)"
					loading={loading}
					showDots
				/>
			</ChartCard>

			<div style={{ marginTop: spacing[6] }}>
				<ChartCard title="Officers" loading={loading}>
					<DataTable
						columns={["Officer", "Balance", "Count", "Ratio"]}
						rows={tableRows}
						loading={loading}
					/>
				</ChartCard>
			</div>
		</div>
	);
}
