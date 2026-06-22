import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import { Field, FieldGrid } from "../caseUi";
import EvidenceReferenceChip from "./EvidenceReferenceChip";
import {
	CONFIDENCE_LABEL,
	type IntakeExtraction,
	type SorComparison,
	type SorMatch,
	type SorMatchResult,
} from "./aiTypes";

const RESULT_LABEL: Record<SorMatchResult, string> = {
	matched: "Matched to member of record",
	partial: "Partial match — review",
	mismatch: "No match — escalate",
};

const RESULT_VARIANT: Record<SorMatchResult, "success" | "warning" | "danger"> =
	{
		matched: "success",
		partial: "warning",
		mismatch: "danger",
	};

const CMP_COLOR: Record<SorComparison["match"], string> = {
	match: "#16a34a",
	partial: "#b45309",
	mismatch: "#dc2626",
};

const CMP_MARK: Record<SorComparison["match"], string> = {
	match: "✓",
	partial: "≈",
	mismatch: "✗",
};

function SorMatchBlock({ sorMatch }: { sorMatch: SorMatch }) {
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
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: spacing[2],
					flexWrap: "wrap",
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
					✨ AI · received vs system of record
				</span>
				<Tag
					label={RESULT_LABEL[sorMatch.result]}
					variant={RESULT_VARIANT[sorMatch.result]}
				/>
				<Tag label={CONFIDENCE_LABEL[sorMatch.confidence]} variant="default" />
			</div>
			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[1] }}
			>
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "1fr 1fr 1fr auto",
						gap: spacing[2],
						fontSize: typography.size.xs,
						fontWeight: typography.weight.semibold,
						color: colors.slate[500],
					}}
				>
					<span>Field</span>
					<span>Received</span>
					<span>System of record</span>
					<span />
				</div>
				{sorMatch.comparisons.map((c) => (
					<div
						key={c.field}
						style={{
							display: "grid",
							gridTemplateColumns: "1fr 1fr 1fr auto",
							gap: spacing[2],
							fontSize: typography.size.sm,
							color: colors.slate[800],
							alignItems: "center",
						}}
					>
						<span style={{ color: colors.slate[500] }}>{c.field}</span>
						<span>{c.received}</span>
						<span>{c.sor}</span>
						<span
							style={{
								color: CMP_COLOR[c.match],
								fontWeight: typography.weight.semibold,
								textAlign: "right",
							}}
						>
							{CMP_MARK[c.match]}
						</span>
					</div>
				))}
			</div>
		</div>
	);
}

/** AI handling of the intake document: SOR identity match + extracted fields. */
export default function IntakeExtractionPanel({
	extraction,
}: { extraction: IntakeExtraction }) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}>
			{extraction.sorMatch && <SorMatchBlock sorMatch={extraction.sorMatch} />}
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: spacing[2],
					flexWrap: "wrap",
				}}
			>
				<Tag label="✨ AI-extracted" variant="info" />
				<Tag
					label={CONFIDENCE_LABEL[extraction.confidence]}
					variant="default"
				/>
				<span
					style={{ fontSize: typography.size.sm, color: colors.slate[500] }}
				>
					from
				</span>
				<EvidenceReferenceChip reference={extraction.sourceDoc} />
			</div>
			<FieldGrid>
				{extraction.fields.map((f) => (
					<Field key={f.label} label={f.label} value={f.value} />
				))}
			</FieldGrid>
		</div>
	);
}
