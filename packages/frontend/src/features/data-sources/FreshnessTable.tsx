import { colors, radii, spacing, typography } from "../../theme/tokens";
import { useGetAvailableMonthsQuery } from "./api";

const SURFACES = [
	{ id: "executive", label: "Executive Summary mart" },
	{ id: "deposits", label: "Deposit Portfolio mart" },
	{ id: "past-due", label: "Past Due / Delinquency mart" },
	{ id: "officer-branch", label: "Officer & Branch mart" },
] as const;

const cardStyle: React.CSSProperties = {
	borderRadius: radii.xl,
	border: `1px solid ${colors.slate[200]}`,
	backgroundColor: colors.white,
	padding: spacing[6],
	marginBottom: spacing[6],
};

function FreshnessRow({ surface, label }: { surface: string; label: string }) {
	const { data, isLoading } = useGetAvailableMonthsQuery(surface);
	const latest = data?.months?.[0];
	const total = data?.months?.length ?? 0;
	return (
		<tr>
			<td style={cellStyle}>{label}</td>
			<td style={cellStyle}>{isLoading ? "…" : (latest ?? "—")}</td>
			<td style={{ ...cellStyle, textAlign: "right" as const }}>
				{isLoading ? "…" : total}
			</td>
		</tr>
	);
}

const cellStyle: React.CSSProperties = {
	padding: `${spacing[3]} ${spacing[4]}`,
	fontSize: typography.size.sm,
	color: colors.slate[700],
	borderBottom: `1px solid ${colors.slate[100]}`,
};

const headStyle: React.CSSProperties = {
	...cellStyle,
	color: colors.slate[500],
	fontWeight: typography.weight.semibold,
	fontSize: typography.size.xs,
	textTransform: "uppercase",
	letterSpacing: "0.05em",
};

export default function FreshnessTable() {
	return (
		<section style={cardStyle} aria-label="Mart freshness">
			<h2
				style={{
					fontSize: typography.size.lg,
					fontWeight: typography.weight.semibold,
					color: colors.slate[900],
					marginTop: 0,
					marginBottom: spacing[4],
				}}
			>
				Mart freshness
			</h2>
			<table style={{ width: "100%", borderCollapse: "collapse" }}>
				<thead>
					<tr>
						<th style={{ ...headStyle, textAlign: "left" as const }}>
							Surface
						</th>
						<th style={{ ...headStyle, textAlign: "left" as const }}>
							Latest month
						</th>
						<th style={{ ...headStyle, textAlign: "right" as const }}>
							Months available
						</th>
					</tr>
				</thead>
				<tbody>
					{SURFACES.map((s) => (
						<FreshnessRow key={s.id} surface={s.id} label={s.label} />
					))}
				</tbody>
			</table>
		</section>
	);
}
