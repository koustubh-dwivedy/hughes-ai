/**
 * Empty-state for the /intelligence page (HUG-179).
 *
 * Shown when no thread is active and nothing is pending. Offers a
 * heading + a small grid of starter questions that submit through the
 * same handler the composer uses. Extracted from IntelligencePage so
 * that file stays under the 300-line structural cap.
 */

import { colors, radii, spacing, typography } from "../../../theme/tokens";

const STARTER_QUESTIONS: readonly string[] = [
	"What's our loan-to-deposit ratio this month?",
	"Show deposit balance by branch as of the latest month.",
	"What's our origination volume this year?",
	"Top 5 deposit products by total balance.",
];

const emptyStateStyle: React.CSSProperties = {
	flex: 1,
	display: "flex",
	flexDirection: "column",
	alignItems: "center",
	justifyContent: "center",
	gap: spacing[4],
	padding: spacing[6],
	textAlign: "center",
};

const emptyHeadingStyle: React.CSSProperties = {
	fontSize: typography.size.xl,
	fontWeight: typography.weight.medium,
	color: colors.slate[800],
	margin: 0,
};

const emptySubheadStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[600],
	maxWidth: 480,
	margin: 0,
};

const suggestionsRowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
	gap: spacing[2],
	width: "min(720px, 100%)",
	marginTop: spacing[2],
};

const suggestionButtonStyle: React.CSSProperties = {
	background: colors.white,
	color: colors.slate[800],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	padding: `${spacing[3]} ${spacing[4]}`,
	cursor: "pointer",
	fontSize: typography.size.sm,
	fontFamily: typography.fontFamily,
	textAlign: "left",
	lineHeight: 1.4,
};

interface Props {
	onSelect: (question: string) => void;
}

export default function EmptyState({ onSelect }: Props) {
	return (
		<div style={emptyStateStyle}>
			<h2 style={emptyHeadingStyle}>Ask Hughes</h2>
			<p style={emptySubheadStyle}>
				Open-ended questions about loans, deposits, originations, delinquency,
				and portfolio performance.
			</p>
			<div style={suggestionsRowStyle}>
				{STARTER_QUESTIONS.map((q) => (
					<button
						key={q}
						type="button"
						style={suggestionButtonStyle}
						onClick={() => onSelect(q)}
					>
						{q}
					</button>
				))}
			</div>
		</div>
	);
}
