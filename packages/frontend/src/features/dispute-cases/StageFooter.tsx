import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { colors, spacing, typography } from "../../theme/tokens";
import Button from "../../ui/primitives/Button";

interface Props {
	/** Index of the stage currently shown. */
	stage: number;
	lastIndex: number;
	/** Whether the case has progressed at least this far (active step). */
	isActive: boolean;
	resolved: boolean;
	canAdvance: boolean;
	/** Reason shown when advancing is blocked. */
	blockedHint?: string;
	onBack: () => void;
	onAdvance: () => void;
	onResolve: () => void;
}

/**
 * Forward/back navigation under a case stage. The reviewer completes the active
 * step to advance; the final stage resolves the case. Earlier (already-done)
 * stages show no forward action — they are revisits.
 */
export default function StageFooter({
	stage,
	lastIndex,
	isActive,
	resolved,
	canAdvance,
	blockedHint,
	onBack,
	onResolve,
	onAdvance,
}: Props) {
	const isLast = stage === lastIndex;
	return (
		<div
			style={{
				display: "flex",
				alignItems: "center",
				justifyContent: "space-between",
				gap: spacing[3],
				marginTop: spacing[5],
				paddingTop: spacing[4],
				borderTop: `1px solid ${colors.slate[200]}`,
				flexWrap: "wrap",
			}}
		>
			<Button
				size="sm"
				variant="subtle"
				disabled={stage === 0}
				onClick={onBack}
				leftSection={<ArrowLeft size={14} />}
			>
				Back
			</Button>

			<div style={{ display: "flex", alignItems: "center", gap: spacing[3] }}>
				{!resolved && isActive && !canAdvance && blockedHint && (
					<span
						style={{ fontSize: typography.size.xs, color: colors.slate[500] }}
					>
						{blockedHint}
					</span>
				)}
				{resolved ? (
					<span
						style={{
							fontSize: typography.size.sm,
							fontWeight: typography.weight.semibold,
							color: "#16a34a",
						}}
					>
						Case resolved
					</span>
				) : !isActive ? (
					<span
						style={{ fontSize: typography.size.xs, color: colors.slate[400] }}
					>
						Completed step — revisiting
					</span>
				) : isLast ? (
					<Button
						size="sm"
						disabled={!canAdvance}
						onClick={onResolve}
						leftSection={<Check size={14} />}
					>
						Resolve case
					</Button>
				) : (
					<Button
						size="sm"
						disabled={!canAdvance}
						onClick={onAdvance}
						rightSection={<ArrowRight size={14} />}
					>
						Complete step & continue
					</Button>
				)}
			</div>
		</div>
	);
}
