import { colors, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import { STANCE_LABEL, stanceVariant } from "../format";
import type { SignalStance, TriangulationRow } from "../types";
import SignalRow from "./SignalRow";

const ORDER: SignalStance[] = ["supports", "against", "inconclusive"];

function StanceGroup({
	stance,
	rows,
	memberName,
}: {
	stance: SignalStance;
	rows: TriangulationRow[];
	memberName?: string;
}) {
	if (rows.length === 0) return null;
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}>
			<span
				style={{
					display: "inline-flex",
					alignItems: "center",
					gap: spacing[2],
					fontSize: typography.size.xs,
					fontWeight: typography.weight.semibold,
					textTransform: "uppercase",
					letterSpacing: "0.05em",
					color: colors.slate[500],
				}}
			>
				{STANCE_LABEL[stance]}
				<Tag label={String(rows.length)} variant={stanceVariant(stance)} />
			</span>
			{rows.map((r) => (
				<SignalRow
					key={`${r.source}-${r.signal}`}
					row={r}
					memberName={memberName}
				/>
			))}
		</div>
	);
}

/**
 * Right column of the investigation review: the evidence, framed by what each
 * signal argues about the fraud claim. A stance summary sits on top; signals
 * group Supports → Against → Inconclusive, each expandable to its resolution,
 * raw datapoints, and source document.
 */
export default function EvidencePanel({
	rows,
	memberName,
}: { rows: TriangulationRow[]; memberName?: string }) {
	const counts = ORDER.map((s) => ({
		stance: s,
		n: rows.filter((r) => r.stance === s).length,
	}));

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			<div
				style={{
					display: "flex",
					gap: spacing[2],
					alignItems: "center",
					flexWrap: "wrap",
				}}
			>
				{counts.map(({ stance, n }) => (
					<Tag
						key={stance}
						label={`${STANCE_LABEL[stance]} ${n}`}
						variant={stanceVariant(stance)}
					/>
				))}
			</div>
			{ORDER.map((s) => (
				<StanceGroup
					key={s}
					stance={s}
					rows={rows.filter((r) => r.stance === s)}
					memberName={memberName}
				/>
			))}
		</div>
	);
}
