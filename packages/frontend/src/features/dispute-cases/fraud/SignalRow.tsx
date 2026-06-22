import { ChevronDown, ChevronRight, Info } from "lucide-react";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tooltip from "../../../ui/primitives/Tooltip";
import EvidenceReferenceChip from "../ai/EvidenceReferenceChip";
import { explainSignal } from "../data/signalLibrary";
import type { SignalDataPoint, TriangulationRow } from "../types";

const DP_COLOR: Record<NonNullable<SignalDataPoint["match"]>, string> = {
	match: "#16a34a",
	mismatch: "#dc2626",
	neutral: colors.slate[400],
};

function DataPoints({ points }: { points: SignalDataPoint[] }) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[1] }}>
			{points.map((d) => (
				<div
					key={d.label}
					style={{
						display: "flex",
						justifyContent: "space-between",
						gap: spacing[3],
						fontSize: typography.size.xs,
					}}
				>
					<span style={{ color: colors.slate[500] }}>{d.label}</span>
					<span
						style={{
							color: d.match ? DP_COLOR[d.match] : colors.slate[800],
							fontWeight: typography.weight.medium,
							textAlign: "right",
						}}
					>
						{d.value}
					</span>
				</div>
			))}
		</div>
	);
}

export default function SignalRow({
	row,
	memberName,
}: { row: TriangulationRow; memberName?: string }) {
	const [open, setOpen] = useState(false);
	const explainer = explainSignal(row.source);

	return (
		<div
			style={{
				borderRadius: radii.md,
				border: `1px solid ${colors.slate[200]}`,
				backgroundColor: colors.white,
				overflow: "hidden",
			}}
		>
			<button
				type="button"
				onClick={() => setOpen((v) => !v)}
				aria-expanded={open}
				style={{
					width: "100%",
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					gap: spacing[3],
					padding: `${spacing[2]} ${spacing[3]}`,
					background: "none",
					border: "none",
					cursor: "pointer",
					textAlign: "left",
				}}
			>
				<span
					style={{ display: "flex", alignItems: "center", gap: spacing[2] }}
				>
					{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
					<span style={{ display: "flex", flexDirection: "column" }}>
						<span
							style={{
								fontSize: typography.size.sm,
								fontWeight: typography.weight.medium,
								color: colors.slate[900],
								display: "inline-flex",
								alignItems: "center",
								gap: spacing[1],
							}}
						>
							{row.source}
							{explainer && (
								<Tooltip label={explainer} multiline w={280}>
									<Info
										size={13}
										color={colors.slate[400]}
										aria-label={explainer}
									/>
								</Tooltip>
							)}
						</span>
						<span
							style={{ fontSize: typography.size.xs, color: colors.slate[500] }}
						>
							{row.signal}
						</span>
					</span>
				</span>
				<span
					style={{ fontSize: typography.size.xs, color: colors.slate[400] }}
				>
					{row.result}
				</span>
			</button>
			{open && (
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						gap: spacing[3],
						padding: `0 ${spacing[3]} ${spacing[3]} ${spacing[6]}`,
					}}
				>
					<div>
						<span
							style={{
								fontSize: typography.size.xs,
								fontWeight: typography.weight.semibold,
								textTransform: "uppercase",
								letterSpacing: "0.05em",
								color: colors.slate[500],
							}}
						>
							How AI resolved this
						</span>
						<p
							style={{
								margin: `${spacing[1]} 0 0`,
								fontSize: typography.size.sm,
								lineHeight: 1.55,
								color: colors.slate[700],
							}}
						>
							{row.resolution}
						</p>
					</div>
					<DataPoints points={row.dataPoints} />
					{row.reference && (
						<EvidenceReferenceChip
							reference={row.reference}
							context={{ memberName }}
						/>
					)}
				</div>
			)}
		</div>
	);
}
