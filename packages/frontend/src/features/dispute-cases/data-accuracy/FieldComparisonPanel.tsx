import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import type { FieldComparison } from "../types";

const headerStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "1.2fr 1fr 1fr auto",
	gap: spacing[2],
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	textTransform: "uppercase",
	letterSpacing: "0.04em",
	color: colors.slate[500],
};

const rowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "1.2fr 1fr 1fr auto",
	gap: spacing[2],
	alignItems: "center",
	fontSize: typography.size.sm,
	color: colors.slate[800],
};

/**
 * The deterministic core: each disputed Metro 2 field, ACDV "as reported" vs the
 * core system of record as of the Date of Account Information, with a match flag.
 */
export default function FieldComparisonPanel({
	fields,
	dateOfAccountInfo,
}: { fields: FieldComparison[]; dateOfAccountInfo: string }) {
	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: spacing[3],
				padding: spacing[4],
				borderRadius: radii.lg,
				border: `1px solid ${colors.slate[200]}`,
				backgroundColor: colors.slate[50],
			}}
		>
			<span
				style={{
					fontSize: typography.size.xs,
					fontWeight: typography.weight.semibold,
					textTransform: "uppercase",
					letterSpacing: "0.05em",
					color: colors.slate[500],
				}}
			>
				Field comparison · as of {dateOfAccountInfo}
			</span>
			<div style={headerStyle}>
				<span>Field</span>
				<span>As reported</span>
				<span>System of record</span>
				<span />
			</div>
			{fields.map((f) => (
				<div key={f.field} style={rowStyle}>
					<span style={{ color: colors.slate[500] }}>{f.field}</span>
					<span>{f.asReported}</span>
					<span>{f.systemOfRecord}</span>
					<Tag
						label={f.match === "match" ? "Match" : "Mismatch"}
						variant={f.match === "match" ? "success" : "danger"}
					/>
				</div>
			))}
		</div>
	);
}
