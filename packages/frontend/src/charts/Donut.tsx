import {
	Cell,
	Label,
	Legend,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
} from "recharts";
import { colors, typography } from "../theme/tokens";

const PALETTE = [
	colors.indigo[500],
	colors.slate[400],
	colors.indigo[700],
	colors.slate[600],
	colors.indigo[100],
	colors.slate[300],
];

interface DonutSlice {
	label: string;
	value: number;
}

interface DonutProps {
	data: DonutSlice[];
	title?: string;
	centerLabel?: string;
	loading?: boolean;
}

/**
 * @example
 * <Donut
 *   data={[{ label: "Current", value: 820 }, { label: "Past Due", value: 43 }]}
 *   title="Loan Status Mix"
 *   centerLabel="$863M"
 * />
 */
export default function Donut({
	data,
	title,
	centerLabel,
	loading = false,
}: DonutProps) {
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

	const rechartData = data.map((d) => ({ name: d.label, value: d.value }));

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
				<PieChart>
					<Pie
						data={rechartData}
						dataKey="value"
						nameKey="name"
						innerRadius="50%"
						outerRadius="80%"
					>
						{rechartData.map((entry, i) => (
							<Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />
						))}
						{centerLabel !== undefined && (
							<Label
								value={centerLabel}
								position="center"
								style={{
									fontSize: typography.size.lg,
									fontWeight: typography.weight.bold,
									fill: colors.slate[800],
								}}
							/>
						)}
					</Pie>
					<Tooltip />
					<Legend />
				</PieChart>
			</ResponsiveContainer>
		</figure>
	);
}
