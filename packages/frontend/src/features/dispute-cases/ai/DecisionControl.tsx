import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Button from "../../../ui/primitives/Button";
import type { HumanAction } from "./aiTypes";

const ACTION_LABEL: Record<HumanAction, string> = {
	approved: "Approved AI recommendation",
	overridden: "Overrode AI recommendation",
	more_info: "Requested more information",
};

interface Props {
	recommendationLabel: string;
	/** Controlled value; when provided with onChange, state is lifted. */
	value?: HumanAction | null;
	onChange?: (action: HumanAction | null) => void;
}

/**
 * The human-in-the-loop resolution control. The agent only recommends; the
 * associate approves, overrides, or asks for more info. Can be uncontrolled
 * (local state) or controlled (lifted) so the recorded decision is shared
 * across stages. Mockup — no persistence.
 */
export default function DecisionControl({
	recommendationLabel,
	value,
	onChange,
}: Props) {
	const [local, setLocal] = useState<HumanAction | null>(null);
	const controlled = value !== undefined;
	const decision = controlled ? value : local;
	const setDecision = (a: HumanAction | null) => {
		if (controlled) onChange?.(a);
		else setLocal(a);
	};

	if (decision) {
		const tone = decision === "overridden" ? "#b45309" : colors.slate[800];
		return (
			<output
				style={{
					display: "flex",
					flexDirection: "column",
					gap: spacing[1],
					padding: spacing[4],
					borderRadius: radii.lg,
					border: `1px solid ${colors.slate[200]}`,
					backgroundColor: colors.slate[50],
				}}
			>
				<span
					style={{
						fontSize: typography.size.sm,
						fontWeight: typography.weight.semibold,
						color: tone,
					}}
				>
					{ACTION_LABEL[decision]}
				</span>
				<span
					style={{ fontSize: typography.size.xs, color: colors.slate[500] }}
				>
					Recommendation: {recommendationLabel} ·{" "}
					<button
						type="button"
						onClick={() => setDecision(null)}
						style={{
							background: "none",
							border: "none",
							padding: 0,
							color: colors.slate[600],
							cursor: "pointer",
							textDecoration: "underline",
							fontSize: "inherit",
						}}
					>
						change
					</button>
				</span>
			</output>
		);
	}

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[3] }}>
			<span style={{ fontSize: typography.size.sm, color: colors.slate[600] }}>
				AI recommends: <strong>{recommendationLabel}</strong>. You decide.
			</span>
			<div style={{ display: "flex", gap: spacing[2], flexWrap: "wrap" }}>
				<Button size="sm" onClick={() => setDecision("approved")}>
					Approve
				</Button>
				<Button
					size="sm"
					variant="default"
					onClick={() => setDecision("overridden")}
				>
					Override
				</Button>
				<Button
					size="sm"
					variant="subtle"
					onClick={() => setDecision("more_info")}
				>
					Request more info
				</Button>
			</div>
		</div>
	);
}
