/**
 * Plan-preview card (HUG-211, L4).
 *
 * Renders the lead's drafted plan with Approve / Abort buttons.
 * Sits in the conversation layout BELOW the chat thread when a
 * `status='draft'` plan exists; chat stays visible above.
 *
 * Status routing for the parent ResearchWorkspace:
 *   draft        → render this PlanPreview
 *   approved/+   → render StepList (HUG-219, S4 — placeholder for now)
 *   missing      → render nothing
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { useAbortPlanMutation, useApprovePlanMutation } from "./api";
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

const approveButtonStyle: React.CSSProperties = {
	background: colors.indigo[700],
	color: colors.white,
	border: "none",
	borderRadius: radii.sm,
	padding: `${spacing[2]} ${spacing[4]}`,
	cursor: "pointer",
	fontSize: typography.size.sm,
	fontWeight: typography.weight.medium,
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

interface Props {
	plan: Plan;
}

export default function PlanPreview({ plan }: Props) {
	const [approve, approveState] = useApprovePlanMutation();
	const [abort, abortState] = useAbortPlanMutation();
	const steps: PlanStepDescriptor[] = plan.plan_json.plan ?? [];
	const reason = plan.plan_json.reason ?? "";
	const summary = plan.plan_json.research_question_summary ?? "Research plan";
	const ids = { threadId: plan.thread_id, planId: plan.plan_id };
	const busy = approveState.isLoading || abortState.isLoading;
	return (
		<aside aria-label="Research plan preview" style={cardStyle}>
			<h3 style={titleStyle}>Proposed research plan</h3>
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
			<div style={buttonRowStyle}>
				<button
					type="button"
					style={abortButtonStyle}
					disabled={busy}
					onClick={() => abort(ids)}
				>
					Cancel
				</button>
				<button
					type="button"
					style={approveButtonStyle}
					disabled={busy}
					onClick={() => approve(ids)}
				>
					{approveState.isLoading ? "Approving…" : "Approve & run"}
				</button>
			</div>
		</aside>
	);
}
