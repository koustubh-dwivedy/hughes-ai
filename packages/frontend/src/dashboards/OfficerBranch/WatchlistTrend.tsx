import LineTrend from "../../charts/LineTrend";
import type { WatchlistTrendPoint } from "../../lib/dashboardApi";

export default function WatchlistTrend({
	data,
}: { data: WatchlistTrendPoint[] }) {
	return (
		<LineTrend
			data={data.map((r) => ({ period: r.month, value: r.count }))}
			title="Watchlist Trend (13 mo.)"
			seriesLabel="Count"
		/>
	);
}
