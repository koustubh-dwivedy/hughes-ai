import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { ReasoningKind, ReasoningStep } from "./aiTypes";

const listStyle: React.CSSProperties = {
	listStyle: "none",
	margin: 0,
	padding: spacing[3],
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	background: colors.slate[50],
};

function kindIcon(kind: ReasoningKind): string {
	if (kind === "tool_call") return "→";
	if (kind === "tool_result") return "←";
	return "•";
}

/** Compact ordered list of the agent's reasoning steps (mockup). */
export default function ReasoningTrace({ steps }: { steps: ReasoningStep[] }) {
	return (
		<ol style={listStyle}>
			{steps.map((s, i) => (
				<li
					key={`${i}-${s.label}`}
					style={{
						display: "flex",
						flexDirection: "column",
						fontSize: typography.size.xs,
					}}
				>
					<span
						style={{
							color: colors.slate[800],
							fontWeight: typography.weight.medium,
						}}
					>
						{kindIcon(s.kind)} {s.label}
					</span>
					{s.detail && (
						<span style={{ color: colors.slate[500], paddingLeft: spacing[3] }}>
							{s.detail}
						</span>
					)}
				</li>
			))}
		</ol>
	);
}
