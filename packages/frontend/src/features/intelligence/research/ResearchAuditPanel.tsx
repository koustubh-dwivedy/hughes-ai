/**
 * Research audit panel (HUG-224, V2).
 *
 * Renders the audit trail for a deep-research-answered message:
 *   - Plan version timeline (collapsed v1 → expanded latest).
 *   - Per-step findings (description + summary_text).
 *   - Lead notes timeline (most-recent first).
 *
 * Designed to live INSIDE ReferencesModal's existing scroll
 * container — the modal owns the chrome (title, close button,
 * keyboard handling); this component owns the research-specific
 * content.
 *
 * For a chat-only answer this component is not rendered (the modal
 * just shows rows + mfQuery + thinking trace, same as today).
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";
import {
	useGetResearchFindingsQuery,
	useGetResearchLeadNotesQuery,
	useGetResearchStepsQuery,
} from "./api";

const sectionStyle: React.CSSProperties = {
	marginTop: spacing[4],
	paddingTop: spacing[4],
	borderTop: `1px solid ${colors.slate[200]}`,
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

const codeStyle: React.CSSProperties = {
	fontFamily: "monospace",
	fontSize: typography.size.xs,
	color: colors.slate[500],
};

const noteStyle: React.CSSProperties = {
	whiteSpace: "pre-wrap",
	padding: `${spacing[2]} ${spacing[3]}`,
	background: colors.slate[50],
	borderRadius: radii.sm,
	marginBottom: spacing[2],
	fontSize: typography.size.sm,
	lineHeight: 1.5,
};

interface Props {
	threadId: string;
	planId: string;
}

export default function ResearchAuditPanel({ threadId, planId }: Props) {
	const { data: stepsData } = useGetResearchStepsQuery({ threadId, planId });
	const { data: findingsData } = useGetResearchFindingsQuery({
		threadId,
		planId,
	});
	const { data: notesData } = useGetResearchLeadNotesQuery({
		threadId,
		planId,
	});
	const steps = stepsData?.steps ?? [];
	const findings = findingsData?.findings ?? [];
	const notes = notesData?.notes ?? [];
	const findingByStep = new Map(findings.map((f) => [f.step_id, f]));
	return (
		<>
			{steps.length > 0 ? (
				<section style={sectionStyle} data-testid="audit-steps">
					<div style={sectionLabelStyle}>Research steps ({steps.length})</div>
					{steps.map((s) => {
						const f = findingByStep.get(s.step_id);
						return (
							<div key={s.step_id} style={rowStyle}>
								<div>
									<span style={codeStyle}>#{s.ordinal}</span> {s.description}{" "}
									<span style={codeStyle}>[{s.status}]</span>
								</div>
								{f?.summary_text ? (
									<div
										style={{
											color: colors.slate[600],
											marginTop: spacing[1],
										}}
									>
										→ {f.summary_text}
									</div>
								) : null}
							</div>
						);
					})}
				</section>
			) : null}
			{notes.length > 0 ? (
				<section style={sectionStyle} data-testid="audit-notes">
					<div style={sectionLabelStyle}>Lead notes ({notes.length})</div>
					{[...notes].reverse().map((n) => (
						<div key={n.note_id} style={noteStyle}>
							<div style={codeStyle}>
								v{n.version} · {new Date(n.created_at).toLocaleString()}
							</div>
							{n.body_md}
						</div>
					))}
				</section>
			) : null}
		</>
	);
}
