import { Info } from "lucide-react";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import Tooltip from "../../../ui/primitives/Tooltip";
import DecisionControl from "../ai/DecisionControl";
import ReasoningTrace from "../ai/ReasoningTrace";
import {
	type AiConfidence,
	type AiInvestigation,
	CONFIDENCE_LABEL,
	type DeterministicCheck,
	type HumanAction,
} from "../ai/aiTypes";
import { explainGate } from "../data/signalLibrary";

const confidenceVariant: Record<
	AiConfidence,
	"danger" | "warning" | "success"
> = {
	low: "danger",
	medium: "warning",
	high: "success",
};

const CHECK_MARK: Record<DeterministicCheck["status"], string> = {
	pass: "✓",
	fail: "✗",
	n_a: "—",
};

function Gate({ check }: { check: DeterministicCheck }) {
	const explainer = explainGate(check.check);
	const color =
		check.status === "pass"
			? "#16a34a"
			: check.status === "fail"
				? "#dc2626"
				: colors.slate[400];
	return (
		<div
			style={{
				display: "flex",
				alignItems: "center",
				gap: spacing[2],
				fontSize: typography.size.sm,
				color: colors.slate[800],
			}}
		>
			<span style={{ color, fontWeight: typography.weight.semibold }}>
				{CHECK_MARK[check.status]}
			</span>
			<span
				style={{
					display: "inline-flex",
					alignItems: "center",
					gap: spacing[1],
				}}
			>
				{check.check}
				{explainer && (
					<Tooltip label={explainer} multiline w={280}>
						<Info size={13} color={colors.slate[400]} aria-label={explainer} />
					</Tooltip>
				)}
			</span>
		</div>
	);
}

interface Props {
	investigation: AiInvestigation;
	decision: HumanAction | null;
	onDecision: (action: HumanAction | null) => void;
}

/**
 * Left column of the investigation review: the agent's synthesis (b) — a
 * verdict referencing the exploration — the deterministic gates, the inline
 * human decision, and the collapsible global reasoning trace.
 */
export default function VerdictPanel({
	investigation,
	decision,
	onDecision,
}: Props) {
	const [showTrace, setShowTrace] = useState(false);
	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: spacing[4],
				padding: spacing[5],
				borderRadius: radii.xl,
				border: `1px solid ${colors.slate[200]}`,
				backgroundColor: colors.white,
				position: "sticky",
				top: spacing[4],
				alignSelf: "flex-start",
			}}
		>
			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}
			>
				<span
					style={{ fontSize: typography.size.xs, color: colors.slate[500] }}
				>
					AI recommendation
				</span>
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
							fontSize: typography.size.lg,
							fontWeight: typography.weight.semibold,
							color: colors.slate[900],
						}}
					>
						{investigation.recommendationLabel}
					</span>
					<Tag
						label={CONFIDENCE_LABEL[investigation.confidence]}
						variant={confidenceVariant[investigation.confidence]}
					/>
				</div>
			</div>

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
					Synthesis
				</span>
				<p
					style={{
						margin: `${spacing[1]} 0 0`,
						fontSize: typography.size.sm,
						lineHeight: 1.6,
						color: colors.slate[700],
					}}
				>
					{investigation.rationale}
				</p>
			</div>

			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[1] }}
			>
				{investigation.deterministicChecks.map((c) => (
					<Gate key={c.check} check={c} />
				))}
			</div>

			<DecisionControl
				recommendationLabel={investigation.recommendationLabel}
				value={decision}
				onChange={onDecision}
			/>

			<div>
				<button
					type="button"
					onClick={() => setShowTrace((v) => !v)}
					style={{
						background: "none",
						border: "none",
						padding: 0,
						color: colors.slate[600],
						cursor: "pointer",
						fontSize: typography.size.sm,
						fontWeight: typography.weight.medium,
					}}
				>
					{showTrace ? "▾" : "▸"} How AI reasoned (
					{investigation.reasoning.length} steps)
				</button>
				{showTrace && (
					<div style={{ marginTop: spacing[2] }}>
						<ReasoningTrace steps={investigation.reasoning} />
					</div>
				)}
			</div>
		</div>
	);
}
