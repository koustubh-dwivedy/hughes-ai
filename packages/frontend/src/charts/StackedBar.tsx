import {
	Bar,
	BarChart,
	CartesianGrid,
	Legend,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { colors, typography } from "../theme/tokens";
import {
	CHART_MARGIN,
	categoricalXAxisProps,
} from "../ui/charts/CategoricalXAxis";

const PALETTE = [
	colors.indigo[500],
	colors.slate[400],
	colors.indigo[700],
	colors.slate[600],
	colors.indigo[100],
	colors.slate[300],
];

interface StackedBarDataPoint {
	period: string;
	[key: string]: number | string;
}

interface StackedBarSeries {
	key: string;
	color?: string;
}

interface StackedBarProps {
	data: StackedBarDataPoint[];
	series: StackedBarSeries[];
	title?: string;
	loading?: boolean;
	/**
	 * "date" (default) renders a recharts XAxis with auto-skipped
	 * labels — fine for short date strings like "Jan-24".
	 * "categorical" renders the shared angled+truncating axis — use
	 * when `period` is a long categorical label (officer name, branch
	 * name) that would otherwise collide.
	 */
	xAxisType?: "date" | "categorical";
}

/**
 * @example
 * <StackedBar
 *   data={[
 *     { period: "Jan-24", "1-14": 12, "15-29": 8, "30-59": 5 },
 *     { period: "Feb-24", "1-14": 10, "15-29": 9, "30-59": 6 },
 *   ]}
 *   series={[{ key: "1-14" }, { key: "15-29" }, { key: "30-59" }]}
 *   title="Delinquency Trend (13 months)"
 * />
 */
export default function StackedBar({
	data,
	series,
	title,
	loading = false,
	xAxisType = "date",
}: StackedBarProps) {
	if (loading) {
		return (
			<output
				aria-label="loading chart"
				style={{
					width: "100%",
					height: 300,
					backgroundColor: colors.slate[100],
					borderRadius: "0.5rem",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					color: colors.slate[400],
					fontSize: typography.size.sm,
				}}
			>
				Loading…
			</output>
		);
	}

	return (
		<figure aria-label={title} style={{ margin: 0, width: "100%" }}>
			{title && (
				<figcaption
					style={{
						fontSize: typography.size.sm,
						fontWeight: typography.weight.semibold,
						color: colors.slate[700],
						marginBottom: "0.5rem",
					}}
				>
					{title}
				</figcaption>
			)}
			<ResponsiveContainer width="100%" height={300}>
				<BarChart
					data={data}
					margin={xAxisType === "categorical" ? CHART_MARGIN : undefined}
				>
					<CartesianGrid strokeDasharray="3 3" stroke={colors.slate[200]} />
					{xAxisType === "categorical" ? (
						<XAxis {...categoricalXAxisProps({ dataKey: "period" })} />
					) : (
						<XAxis
							dataKey="period"
							tick={{ fontSize: 11, fill: colors.slate[500] }}
						/>
					)}
					<YAxis tick={{ fontSize: 11, fill: colors.slate[500] }} />
					<Tooltip />
					<Legend />
					{series.map((s, i) => (
						<Bar
							key={s.key}
							dataKey={s.key}
							stackId="a"
							fill={s.color ?? PALETTE[i % PALETTE.length]}
						/>
					))}
				</BarChart>
			</ResponsiveContainer>
		</figure>
	);
}
