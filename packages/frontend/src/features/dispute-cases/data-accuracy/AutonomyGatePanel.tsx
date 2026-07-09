import { Check, Minus, X } from "lucide-react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";
import type { CheckStatus, DeterministicCheck } from "../ai/aiTypes";
import { RESPONSE_CODE_LABEL, type ResponseCode } from "../types";

const ICON: Record<CheckStatus, React.ReactNode> = {
	pass: <Check size={12} />,
	fail: <X size={12} />,
	n_a: <Minus size={12} />,
};

const ICON_BG: Record<CheckStatus, string> = {
	pass: "#16a34a",
	fail: "#e11d48",
	n_a: colors.slate[300],
};

/**
 * The three autonomy gates (from the research) as pass/fail checks, plus the
 * recommended e-OSCAR response code and whether the agent may act autonomously.
 */
export default function AutonomyGatePanel({
	checks,
	recommendedResponse,
	autonomyMode,
}: {
	checks: DeterministicCheck[];
	recommendedResponse: ResponseCode;
	autonomyMode: "autonomous" | "draft_for_human";
}) {
	const autonomous = autonomyMode === "autonomous";
	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: spacing[3],
				padding: spacing[4],
				borderRadius: radii.lg,
				border: `1px solid ${colors.slate[200]}`,
				backgroundColor: colors.white,
			}}
		>
			<div style={{ display: "flex", gap: spacing[2], flexWrap: "wrap" }}>
				<Tag label="Autonomy gates" variant="default" />
				<Tag
					label={autonomous ? "All gates passed" : "Gate tripped — review"}
					variant={autonomous ? "success" : "warning"}
				/>
			</div>
			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}
			>
				{checks.map((c) => (
					<div
						key={c.check}
						style={{
							display: "flex",
							alignItems: "center",
							gap: spacing[2],
							fontSize: typography.size.sm,
							color: colors.slate[800],
						}}
					>
						<span
							style={{
								display: "inline-flex",
								alignItems: "center",
								justifyContent: "center",
								width: 18,
								height: 18,
								borderRadius: "9999px",
								backgroundColor: ICON_BG[c.status],
								color: colors.white,
								flexShrink: 0,
							}}
						>
							{ICON[c.status]}
						</span>
						<span style={{ fontWeight: typography.weight.medium }}>
							{c.check}
						</span>
						<span
							style={{ color: colors.slate[500], fontSize: typography.size.xs }}
						>
							— {c.basis}
						</span>
					</div>
				))}
			</div>
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: spacing[2],
					flexWrap: "wrap",
					paddingTop: spacing[3],
					borderTop: `1px solid ${colors.slate[200]}`,
				}}
			>
				<span
					style={{ fontSize: typography.size.sm, color: colors.slate[600] }}
				>
					Recommended e-OSCAR response:
				</span>
				<Tag
					label={`${recommendedResponse} — ${RESPONSE_CODE_LABEL[recommendedResponse]}`}
					variant="info"
				/>
			</div>
		</div>
	);
}
