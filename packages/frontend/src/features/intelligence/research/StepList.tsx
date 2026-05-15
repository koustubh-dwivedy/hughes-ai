/**
 * Step list (HUG-219, S4).
 *
 * Renders every step under a research plan with a status chip
 * (pending / running / complete / failed). Multiple steps can sit
 * in `running` simultaneously when the parallel coordinator (HUG-218)
 * dispatches a batch.
 *
 * Updates via `useGetResearchStepsQuery`'s tag invalidation:
 *   - When the user approves a plan: the mutation invalidates
 *     `ResearchSteps`, the query refetches, the new pending rows
 *     appear.
 *   - During execution: SSE events from the backend dispatch tag
 *     invalidations (HUG-222 wires that). For now polling on
 *     `useGetResearchStepsQuery` is the source of truth.
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { useGetResearchStepsQuery } from "./api";
import type { Step, StepStatus } from "./types";

const containerStyle: React.CSSProperties = {
	background: colors.white,
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	padding: spacing[3],
	margin: `${spacing[3]} 0`,
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
};

const headerStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	fontWeight: typography.weight.medium,
	color: colors.slate[700],
	margin: 0,
};

const rowStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	gap: spacing[3],
	padding: `${spacing[2]} ${spacing[1]}`,
	borderTop: `1px solid ${colors.slate[100]}`,
};

const ordinalStyle: React.CSSProperties = {
	fontFamily: typography.fontFamily,
	color: colors.slate[500],
	fontSize: typography.size.xs,
	width: 24,
};

const descStyle: React.CSSProperties = {
	flex: 1,
	fontSize: typography.size.sm,
	color: colors.slate[800],
	lineHeight: 1.4,
};

// Monochrome palette — only slate + indigo available in theme tokens.
// Status differentiation comes from shade contrast + the chip label.
const STATUS_STYLE: Record<StepStatus, React.CSSProperties> = {
	pending: { background: colors.slate[100], color: colors.slate[600] },
	running: { background: colors.indigo[100], color: colors.indigo[700] },
	complete: { background: colors.slate[200], color: colors.slate[800] },
	failed: { background: colors.slate[800], color: colors.white },
	skipped: { background: colors.slate[100], color: colors.slate[400] },
};

const chipBaseStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	padding: "2px 8px",
	borderRadius: radii.sm,
	textTransform: "uppercase",
	letterSpacing: 0.4,
};

interface StatusChipProps {
	status: StepStatus;
}

function StatusChip({ status }: StatusChipProps) {
	return (
		<span
			data-testid={`status-${status}`}
			style={{ ...chipBaseStyle, ...STATUS_STYLE[status] }}
		>
			{status === "running" ? "● running" : status}
		</span>
	);
}

interface Props {
	threadId: string;
	planId: string;
}

export default function StepList({ threadId, planId }: Props) {
	const { data } = useGetResearchStepsQuery({ threadId, planId });
	const steps: Step[] = data?.steps ?? [];
	if (steps.length === 0) return null;
	const sorted = [...steps].sort((a, b) => a.ordinal - b.ordinal);
	return (
		<section aria-label="Research steps" style={containerStyle}>
			<h3 style={headerStyle}>Research steps</h3>
			{sorted.map((s) => (
				<div key={s.step_id} style={rowStyle}>
					<span style={ordinalStyle}>#{s.ordinal}</span>
					<span style={descStyle}>{s.description}</span>
					<StatusChip status={s.status} />
				</div>
			))}
		</section>
	);
}
