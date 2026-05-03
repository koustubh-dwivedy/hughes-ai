import { colors, radii, spacing, typography } from "../../theme/tokens";
import PageHeader from "../../ui/primitives/PageHeader";
import { useGetTrustQuery } from "../trust/api";
import FreshnessTable from "./FreshnessTable";

const cardStyle: React.CSSProperties = {
	borderRadius: radii.xl,
	border: `1px solid ${colors.slate[200]}`,
	backgroundColor: colors.white,
	padding: spacing[6],
	marginBottom: spacing[6],
};

const statRowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
	gap: spacing[4],
};

const statLabelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.05em",
	marginBottom: spacing[1],
};

const statValueStyle: React.CSSProperties = {
	fontSize: typography.size["2xl"],
	fontWeight: typography.weight.semibold,
	color: colors.slate[900],
};

export default function DataSources() {
	const { data: trust, isLoading, isError } = useGetTrustQuery();

	if (isLoading) {
		return (
			<div>
				<PageHeader
					title="Sources & Freshness"
					eyebrow="Data"
					subtitle="What feeds the dashboards, when it last refreshed, and what to know before quoting a number."
				/>
				<p style={{ color: colors.slate[500] }}>Loading trust signals…</p>
			</div>
		);
	}

	if (isError || !trust) {
		return (
			<div>
				<PageHeader title="Sources & Freshness" eyebrow="Data" />
				<p role="alert">Failed to load trust signals.</p>
			</div>
		);
	}

	const matchPct = (trust.reconciliation_match_rate * 100).toFixed(1);
	const recoTone =
		trust.reconciliation_match_rate >= 0.99
			? "#16a34a"
			: trust.reconciliation_match_rate >= 0.95
				? "#d97706"
				: "#dc2626";

	return (
		<div>
			<PageHeader
				title="Sources & Freshness"
				eyebrow="Data"
				subtitle="What feeds the dashboards, when it last refreshed, and what to know before quoting a number."
			/>

			<section style={cardStyle} aria-label="Source counts">
				<h2
					style={{
						fontSize: typography.size.lg,
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
						marginTop: 0,
						marginBottom: spacing[4],
					}}
				>
					Source records
				</h2>
				<div style={statRowStyle}>
					<div>
						<p style={statLabelStyle}>Origence (loan origination)</p>
						<p style={statValueStyle}>
							{trust.origence_row_count.toLocaleString()}
						</p>
					</div>
					<div>
						<p style={statLabelStyle}>Symitar (core banking)</p>
						<p style={statValueStyle}>
							{trust.symitar_row_count.toLocaleString()}
						</p>
					</div>
					<div>
						<p style={statLabelStyle}>Reconciliation match</p>
						<p style={{ ...statValueStyle, color: recoTone }}>{matchPct}%</p>
					</div>
				</div>
			</section>

			<FreshnessTable />

			<section style={cardStyle} aria-label="Known caveats">
				<h2
					style={{
						fontSize: typography.size.lg,
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
						marginTop: 0,
						marginBottom: spacing[3],
					}}
				>
					Known caveats
				</h2>
				{trust.known_caveats.length === 0 ? (
					<p style={{ color: colors.slate[500], margin: 0 }}>
						No caveats currently flagged.
					</p>
				) : (
					<ul
						style={{
							margin: 0,
							paddingLeft: spacing[6],
							color: colors.slate[700],
							fontSize: typography.size.sm,
							lineHeight: 1.6,
						}}
					>
						{trust.known_caveats.map((c) => (
							<li key={c}>{c}</li>
						))}
					</ul>
				)}
			</section>
		</div>
	);
}
