/**
 * Thinking-trace renderer extracted from ReferencesModal to keep the
 * modal under the 300-line structural cap. Renders the ordered list of
 * agent steps (tool_call, tool_result, thinking_text) emitted during
 * one turn — the persistent record the user inspects post-completion.
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { ThreadTraceEntry } from "../api";

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

const itemStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "auto 1fr",
	columnGap: spacing[3],
	rowGap: spacing[1],
	fontSize: typography.size.xs,
};

const stepBadgeStyle: React.CSSProperties = {
	background: colors.indigo[700],
	color: colors.white,
	borderRadius: radii.sm,
	padding: `0 ${spacing[2]}`,
	fontWeight: typography.weight.medium,
	alignSelf: "start",
	minWidth: 28,
	textAlign: "center",
};

const labelStyle: React.CSSProperties = {
	color: colors.slate[800],
	fontWeight: typography.weight.medium,
};

const metaStyle: React.CSSProperties = {
	gridColumn: "2 / -1",
	color: colors.slate[500],
	fontSize: typography.size.xs,
};

function kindIcon(kind: string): string {
	if (kind === "tool_call") return "→";
	if (kind === "tool_result") return "←";
	if (kind === "thinking_text") return "•";
	return "·";
}

export default function ReferencesTrace({
	entries,
}: {
	entries: ThreadTraceEntry[];
}) {
	return (
		<ol style={listStyle}>
			{entries.map((entry) => (
				<li key={`${entry.step}-${entry.kind}-${entry.at}`} style={itemStyle}>
					<span style={stepBadgeStyle} aria-label={`step ${entry.step}`}>
						{entry.step}
					</span>
					<span style={labelStyle}>
						{kindIcon(entry.kind)} {entry.label}
					</span>
					<span style={metaStyle}>
						{entry.kind}
						{entry.tool ? ` · ${entry.tool}` : ""}
					</span>
				</li>
			))}
		</ol>
	);
}
