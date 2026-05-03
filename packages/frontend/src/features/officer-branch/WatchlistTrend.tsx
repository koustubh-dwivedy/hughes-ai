import LineTrend from "../../charts/LineTrend";
import type { WatchlistTrendPoint } from "../../shared/api/dashboardApi";
import InsightCard from "../../shared/components/InsightCard";
import { watchlistTrendInsight } from "../../shared/insights/rules";
import { spacing } from "../../theme/tokens";

export default function WatchlistTrend({
	data,
}: { data: WatchlistTrendPoint[] }) {
	if (data.length === 0) return null;
	const points = data.map((r) => ({ period: r.month, value: r.count }));
	const insight = watchlistTrendInsight(
		data.map((r) => ({ month: r.month, count: r.count })),
	);
	return (
		<div style={{ marginBottom: spacing[6] }}>
			<LineTrend data={points} title="Loans under watch" seriesLabel="Count" />
			<div style={{ marginTop: spacing[3] }}>
				<InsightCard {...insight} />
			</div>
		</div>
	);
}
