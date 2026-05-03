import { emit } from "../../../shared/telemetry/client";
import { colors, radii, spacing, typography } from "../../../theme/tokens";

interface Props {
	onSelect: (prompt: string) => void;
}

const PROMPTS: readonly string[] = [
	"How many active loans do we have?",
	"Show past-due ratio for the last 13 months",
	"Top 10 borrowers by balance",
	"Deposit mix breakdown by product",
	"Officer with the highest delinquency rate",
	"What is the month-to-date change in total deposits?",
] as const;

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	flexWrap: "wrap" as const,
	gap: spacing[2],
	padding: spacing[4],
};

const headingStyle: React.CSSProperties = {
	width: "100%",
	margin: 0,
	marginBottom: spacing[2],
	fontSize: typography.size.sm,
	fontWeight: typography.weight.medium,
	color: colors.slate[600],
};

const chipStyle: React.CSSProperties = {
	background: colors.white,
	color: colors.slate[800],
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.lg,
	padding: `${spacing[2]} ${spacing[3]}`,
	fontSize: typography.size.sm,
	fontFamily: typography.fontFamily,
	cursor: "pointer",
	textAlign: "left",
	boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
};

export default function SuggestedPrompts({ onSelect }: Props) {
	function handleClick(prompt: string) {
		emit({ type: "chat.suggested_prompt.clicked", prompt });
		onSelect(prompt);
	}

	return (
		<section aria-label="Suggested prompts" style={wrapperStyle}>
			<h2 style={headingStyle}>Try one of these to get started</h2>
			{PROMPTS.map((prompt) => (
				<button
					key={prompt}
					type="button"
					onClick={() => handleClick(prompt)}
					style={chipStyle}
				>
					{prompt}
				</button>
			))}
		</section>
	);
}

export { PROMPTS };
