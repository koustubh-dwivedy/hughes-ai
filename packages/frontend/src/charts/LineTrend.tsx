import {
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { colors, typography } from "../theme/tokens";

interface LineTrendDataPoint {
	period: string;
	value: number;
}

interface LineTrendProps {
	data: LineTrendDataPoint[];
	seriesLabel?: string;
	title?: string;
	loading?: boolean;
	showDots?: boolean;
}

/**
 * @example
 * <LineTrend
 *   data={[
 *     { period: "Jan-24", value: 2.1 },
 *     { period: "Feb-24", value: 2.3 },
 *     { period: "Mar-24", value: 2.0 },
 *   ]}
 *   seriesLabel="Delinquency Rate (%)"
 *   title="12-Month Delinquency Trend"
 * />
 */
export default function LineTrend({
	data,
	seriesLabel = "Value",
	title,
	loading = false,
	showDots = false,
}: LineTrendProps) {
	if (loading) {
		return (
			<output
				aria-label="loading chart"
				style={{
					width: 600,
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
		<figure aria-label={title} style={{ margin: 0 }}>
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
			<LineChart width={600} height={300} data={data}>
				<CartesianGrid strokeDasharray="3 3" stroke={colors.slate[200]} />
				<XAxis
					dataKey="period"
					tick={{ fontSize: 11, fill: colors.slate[500] }}
				/>
				<YAxis tick={{ fontSize: 11, fill: colors.slate[500] }} />
				<Tooltip />
				<Legend />
				<Line
					dataKey="value"
					name={seriesLabel}
					type="monotone"
					stroke={colors.indigo[500]}
					dot={showDots ? { r: 3 } : false}
					activeDot={{ r: 4 }}
				/>
			</LineChart>
		</figure>
	);
}
