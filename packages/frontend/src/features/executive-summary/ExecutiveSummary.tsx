import Combo from "../../charts/Combo";
import LineTrend from "../../charts/LineTrend";
import DashboardHeadline from "../../shared/components/DashboardHeadline";
import InsightCard from "../../shared/components/InsightCard";
import MonthSelector from "../../shared/components/MonthSelector";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { executiveHeadline } from "../../shared/insights/headlines";
import {
	loanRateSpreadInsight,
	ratioTrendInsight,
} from "../../shared/insights/rules";
import { emit } from "../../shared/telemetry/client";
import { spacing } from "../../theme/tokens";
import { formatAxisDate, formatAxisPercent } from "../../ui/charts/formatters";
import ChartCard from "../../ui/primitives/ChartCard";
import KpiTile from "../../ui/primitives/KpiTile";
import type { KpiTileProps } from "../../ui/primitives/KpiTile/types";
import PageHeader from "../../ui/primitives/PageHeader";
import { useExecutiveSummary } from "./api";
import { depositsTiles, efficiencyTiles, loansTiles, riskTiles } from "./tiles";

const LOADING_KEYS = ["a", "b", "c", "d"];

const sectionStyle: React.CSSProperties = { marginBottom: spacing[6] };
const clusterLabelStyle: React.CSSProperties = {
	fontSize: "0.75rem",
	fontWeight: 600,
	textTransform: "uppercase" as const,
	letterSpacing: "0.05em",
	color: "#64748b",
	margin: `0 0 ${spacing[3]}`,
};
const tilesRowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
	gap: spacing[4],
};

function onTileClick(kpi_id: string, value: number) {
	emit({ type: "kpi.tile.clicked", kpi_id, value });
}

function ClusterRow({
	label,
	tiles,
	loading,
	skeletonCount,
}: {
	label: string;
	tiles: KpiTileProps[];
	loading: boolean;
	skeletonCount: number;
}) {
	return (
		<div style={sectionStyle}>
			<p style={clusterLabelStyle}>{label}</p>
			<div style={tilesRowStyle}>
				{loading
					? LOADING_KEYS.slice(0, skeletonCount).map((k) => (
							<KpiTile key={k} label="" value="" loading />
						))
					: tiles.map((props) => <KpiTile key={props.label} {...props} />)}
			</div>
		</div>
	);
}

export default function ExecutiveSummary() {
	const { asOfDate } = useDashboardContext();
	const { data, loading, isError } = useExecutiveSummary({ asOfDate });

	if (isError) {
		return (
			<div>
				<PageHeader title="Executive Summary" eyebrow="Overview" />
				<p role="alert">Failed to load executive summary.</p>
			</div>
		);
	}

	const loans = data ? loansTiles(data, onTileClick) : [];
	const deposits = data ? depositsTiles(data, onTileClick) : [];
	const risk = data ? riskTiles(data, onTileClick) : [];
	const efficiency = data ? efficiencyTiles(data, onTileClick) : [];

	const loansTrend = data
		? data.kpi_trend_13_months.map((d) => ({
				period: formatAxisDate(d.month),
				bar: d.total_loans_balance / 1_000_000,
				line: d.rate_spread * 100,
			}))
		: [];

	const ratioTrend = data
		? data.kpi_trend_13_months.map((d) => ({
				period: formatAxisDate(d.month),
				value: Number(
					formatAxisPercent(d.blended_past_due_ratio * 100).replace("%", ""),
				),
			}))
		: [];

	return (
		<div>
			<PageHeader
				title="Executive Summary"
				eyebrow="Overview"
				actions={<MonthSelector surface="executive" />}
			/>
			{data && <DashboardHeadline headline={executiveHeadline(data)} />}
			<ClusterRow
				label="Loans"
				tiles={loans}
				loading={loading}
				skeletonCount={3}
			/>
			<ClusterRow
				label="Deposits"
				tiles={deposits}
				loading={loading}
				skeletonCount={3}
			/>
			<ClusterRow
				label="Risk"
				tiles={risk}
				loading={loading}
				skeletonCount={2}
			/>
			<ClusterRow
				label="Efficiency"
				tiles={efficiency}
				loading={loading}
				skeletonCount={1}
			/>
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
					gap: spacing[6],
					marginBottom: spacing[6],
				}}
			>
				<ChartCard
					title="Loan Book vs. Margin (13 mo.)"
					subtitle="Bars: total loans ($M). Line: loan yield − deposit cost (%)."
					loading={loading}
					footer={
						!loading && <InsightCard {...loanRateSpreadInsight(loansTrend)} />
					}
				>
					<Combo
						data={loansTrend}
						barLabel="Loans ($M)"
						lineLabel="Margin (%)"
						loading={loading}
					/>
				</ChartCard>
				<ChartCard
					title="Past-Due Ratio (13 mo.)"
					subtitle="Share of loan balance 30+ days late"
					loading={loading}
					footer={
						!loading && <InsightCard {...ratioTrendInsight(ratioTrend)} />
					}
				>
					<LineTrend
						data={ratioTrend}
						seriesLabel="Past Due Ratio (%)"
						loading={loading}
					/>
				</ChartCard>
			</div>
		</div>
	);
}
