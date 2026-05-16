/**
 * SubagentCallList — renders the `subagent_calls` rows for a plan.
 *
 * HUG-245: backs the deep-research audit panel for the new autonomous
 * lead-agent path (HUG-244). Each row shows the prompt the lead handed
 * to a worker subagent + the worker's status + summary (when complete).
 * Multiple "running" chips can be visible simultaneously when the lead
 * dispatches subagents in parallel.
 *
 * Designed to live inside ResearchAuditPanel — no own chrome.
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { useGetResearchSubagentCallsQuery } from "./api";
import type { SubagentCallStatus } from "./types";

interface Props {
	threadId: string;
	planId: string;
}

const STATUS_STYLES: Record<SubagentCallStatus, React.CSSProperties> = {
	pending: { background: colors.slate[100], color: colors.slate[600] },
	running: { background: colors.indigo[100], color: colors.indigo[700] },
	complete: { background: "#d1fae5", color: "#065f46" },
	failed: { background: "#fee2e2", color: "#991b1b" },
};

const sectionLabelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: 0.6,
	marginBottom: spacing[2],
};

const rowStyle: React.CSSProperties = {
	padding: `${spacing[2]} 0`,
	borderTop: `1px solid ${colors.slate[100]}`,
	fontSize: typography.size.sm,
};

const chipStyle: React.CSSProperties = {
	display: "inline-block",
	padding: `0 ${spacing[2]}`,
	borderRadius: radii.sm,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	marginRight: spacing[2],
};

export default function SubagentCallList({ threadId, planId }: Props) {
	const { data, isLoading, isError } = useGetResearchSubagentCallsQuery({
		threadId,
		planId,
	});
	if (isLoading) {
		return (
			<div style={{ color: colors.slate[500] }}>Loading subagent calls…</div>
		);
	}
	if (isError) {
		return (
			<div role="alert" style={{ color: "#991b1b" }}>
				Failed to load subagent calls.
			</div>
		);
	}
	const calls = data?.calls ?? [];
	if (calls.length === 0) {
		return null;
	}
	return (
		<section data-testid="audit-subagent-calls">
			<div style={sectionLabelStyle}>Subagent calls ({calls.length})</div>
			{calls.map((call) => (
				<div key={call.call_id} style={rowStyle}>
					<div>
						<span style={{ ...chipStyle, ...STATUS_STYLES[call.status] }}>
							{call.status}
						</span>
						{call.plan_step_ordinal != null ? (
							<span
								style={{
									fontFamily: "monospace",
									fontSize: typography.size.xs,
									color: colors.slate[500],
									marginRight: spacing[2],
								}}
							>
								#step{call.plan_step_ordinal}
							</span>
						) : null}
						{call.prompt}
					</div>
					{call.summary_text ? (
						<div
							style={{
								color: colors.slate[600],
								marginTop: spacing[1],
							}}
						>
							→ {call.summary_text}
						</div>
					) : null}
					{call.error_text ? (
						<div
							style={{ color: "#991b1b", marginTop: spacing[1] }}
							role="alert"
						>
							{call.error_text}
						</div>
					) : null}
				</div>
			))}
		</section>
	);
}
