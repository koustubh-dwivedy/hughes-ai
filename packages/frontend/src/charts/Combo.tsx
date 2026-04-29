import {
	Bar,
	CartesianGrid,
	ComposedChart,
	Legend,
	Line,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { colors, typography } from "../theme/tokens";

interface ComboDataPoint {
	period: string;
	bar: number;
	line: number;
}

interface ComboProps {
	data: ComboDataPoint[];
	barLabel?: string;
	lineLabel?: string;
	title?: string;
	loading?: boolean;
}

/**
 * @example
 * <Combo
 *   data={[
 *     { period: "Jan-24", bar: 42.5, line: 6.8 },
 *     { period: "Feb-24", bar: 43.1, line: 6.9 },
 *   ]}
 *   barLabel="Loan Balance ($M)"
 *   lineLabel="Avg Rate (%)"
 *   title="Balance vs. Rate"
 * />
 */
export default function Combo({
	data,
	barLabel = "Bar",
	lineLabel = "Line",
	title,
	loading = false,
}: ComboProps) {
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
			<ComposedChart width={600} height={300} data={data}>
				<CartesianGrid strokeDasharray="3 3" stroke={colors.slate[200]} />
				<XAxis
					dataKey="period"
					tick={{ fontSize: 11, fill: colors.slate[500] }}
				/>
				<YAxis
					yAxisId="left"
					tick={{ fontSize: 11, fill: colors.slate[500] }}
				/>
				<YAxis
					yAxisId="right"
					orientation="right"
					tick={{ fontSize: 11, fill: colors.slate[500] }}
				/>
				<Tooltip />
				<Legend />
				<Bar
					yAxisId="left"
					dataKey="bar"
					name={barLabel}
					fill={colors.indigo[500]}
				/>
				<Line
					yAxisId="right"
					dataKey="line"
					name={lineLabel}
					type="monotone"
					stroke={colors.slate[600]}
					dot={false}
				/>
			</ComposedChart>
		</figure>
	);
}
