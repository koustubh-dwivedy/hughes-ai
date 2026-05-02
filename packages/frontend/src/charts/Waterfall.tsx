import {
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { colors, typography } from "../theme/tokens";

const STEP_POSITIVE = "#16a34a";
const STEP_NEGATIVE = "#dc2626";
const STEP_TOTAL = colors.indigo[500];

interface WaterfallStep {
	label: string;
	value: number;
	isTotal?: boolean;
}

interface ChartRow {
	label: string;
	base: number;
	delta_abs: number;
	positive: boolean;
	isTotal: boolean;
}

interface WaterfallProps {
	data: WaterfallStep[];
	title?: string;
	loading?: boolean;
}

/**
 * @example
 * <Waterfall
 *   data={[
 *     { label: "Start", value: 100, isTotal: true },
 *     { label: "New Loans", value: 50 },
 *     { label: "Payoffs", value: -30 },
 *     { label: "End", value: 120, isTotal: true },
 *   ]}
 *   title="Loan Balance Waterfall ($M)"
 * />
 */
export default function Waterfall({
	data,
	title,
	loading = false,
}: WaterfallProps) {
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

	let running = 0;
	const chartData: ChartRow[] = data.map((step) => {
		if (step.isTotal) {
			running = step.value;
			return {
				label: step.label,
				base: 0,
				delta_abs: step.value,
				positive: step.value >= 0,
				isTotal: true,
			};
		}
		const start = running;
		running += step.value;
		const base = Math.min(start, running);
		return {
			label: step.label,
			base,
			delta_abs: Math.abs(step.value),
			positive: step.value >= 0,
			isTotal: false,
		};
	});

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
				<BarChart data={chartData}>
					<CartesianGrid strokeDasharray="3 3" stroke={colors.slate[200]} />
					<XAxis
						dataKey="label"
						interval={0}
						tick={{ fontSize: 11, fill: colors.slate[500] }}
					/>
					<YAxis tick={{ fontSize: 11, fill: colors.slate[500] }} />
					<Tooltip />
					<Bar
						dataKey="base"
						stackId="a"
						fill="transparent"
						legendType="none"
					/>
					<Bar dataKey="delta_abs" stackId="a" name="Change">
						{chartData.map((d) => (
							<Cell
								key={d.label}
								fill={
									d.isTotal
										? STEP_TOTAL
										: d.positive
											? STEP_POSITIVE
											: STEP_NEGATIVE
								}
							/>
						))}
					</Bar>
				</BarChart>
			</ResponsiveContainer>
		</figure>
	);
}
