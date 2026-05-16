/**
 * Plan-preview card (HUG-211 → HUG-245 reframe → Fix D, 2026-05-17).
 *
 * Informational-only view of the lead agent's currently-active research
 * plan. Renders the proposed steps + a version badge so the user can
 * see which iteration is active when the lead has called propose_plan
 * multiple times. The Approve gate is gone (HUG-247 Phase B deleted
 * the /approve route); only the Abort kill-switch remains.
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { useAbortPlanMutation } from "./api";
import type { Plan, PlanStepDescriptor } from "./types";

const cardStyle: React.CSSProperties = {
	background: colors.white,
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	padding: spacing[4],
	margin: `${spacing[3]} 0`,
	display: "flex",
	flexDirection: "column",
	gap: spacing[3],
};

const titleStyle: React.CSSProperties = {
	fontSize: typography.size.lg,
	fontWeight: typography.weight.medium,
	color: colors.slate[800],
	margin: 0,
};

const reasonStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[600],
	margin: 0,
};

const stepListStyle: React.CSSProperties = {
	listStyle: "decimal",
	paddingLeft: spacing[5],
	margin: 0,
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
};

const stepItemStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[700],
	lineHeight: 1.5,
};

const buttonRowStyle: React.CSSProperties = {
	display: "flex",
	gap: spacing[2],
	justifyContent: "flex-end",
	marginTop: spacing[1],
};

const abortButtonStyle: React.CSSProperties = {
	background: colors.white,
	color: colors.slate[700],
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.sm,
	padding: `${spacing[2]} ${spacing[4]}`,
	cursor: "pointer",
	fontSize: typography.size.sm,
};

const versionBadgeStyle: React.CSSProperties = {
	display: "inline-block",
	background: colors.indigo[100] ?? "#e0e7ff",
	color: colors.indigo[700],
	borderRadius: radii.sm,
	padding: `0 ${spacing[2]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	marginLeft: spacing[2],
};

interface Props {
	plan: Plan;
}

export default function PlanPreview({ plan }: Props) {
	const [abort, abortState] = useAbortPlanMutation();
	const steps: PlanStepDescriptor[] = plan.plan_json.plan ?? [];
	const reason = plan.plan_json.reason ?? "";
	const summary = plan.plan_json.research_question_summary ?? "Research plan";
	const ids = { threadId: plan.thread_id, planId: plan.plan_id };
	const aborted = plan.status === "aborted";
	const showAbort =
		!aborted && plan.status !== "complete" && plan.status !== "failed";
	return (
		<aside aria-label="Research plan preview" style={cardStyle}>
			<h3 style={titleStyle}>
				Research plan
				<span style={versionBadgeStyle} aria-label={`version ${plan.version}`}>
					v{plan.version}
				</span>
				<span
					style={{
						...versionBadgeStyle,
						background: colors.slate[100],
						color: colors.slate[600],
					}}
				>
					{plan.status}
				</span>
			</h3>
			<p style={reasonStyle}>
				<strong>{summary}</strong>
				{reason ? ` — ${reason}` : null}
			</p>
			<ol style={stepListStyle}>
				{steps.map((s) => (
					<li key={s.ordinal} style={stepItemStyle}>
						{s.description}
						{s.dependencies.length > 0 ? (
							<span style={{ color: colors.slate[500] }}>
								{" "}
								(depends on step{s.dependencies.length > 1 ? "s" : ""}{" "}
								{s.dependencies.join(", ")})
							</span>
						) : null}
					</li>
				))}
			</ol>
			{showAbort ? (
				<div style={buttonRowStyle}>
					<button
						type="button"
						style={abortButtonStyle}
						disabled={abortState.isLoading}
						onClick={() => abort(ids)}
					>
						{abortState.isLoading ? "Stopping…" : "Stop research"}
					</button>
				</div>
			) : null}
		</aside>
	);
}
