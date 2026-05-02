import { colors, radii, spacing, typography } from "../../theme/tokens";

interface Props {
	question: string;
	timestamp: number;
}

const cardStyle: React.CSSProperties = {
	alignSelf: "flex-end",
	maxWidth: "70%",
	padding: `${spacing[3]} ${spacing[4]}`,
	background: colors.indigo[600],
	color: colors.white,
	borderRadius: radii.lg,
	fontSize: typography.size.sm,
	lineHeight: 1.5,
	whiteSpace: "pre-wrap" as const,
	wordBreak: "break-word" as const,
};

const timeStyle: React.CSSProperties = {
	display: "block",
	marginTop: spacing[1],
	fontSize: typography.size.xs,
	color: colors.indigo[100],
	textAlign: "right",
};

export default function UserMessage({ question, timestamp }: Props) {
	const time = new Date(timestamp).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
	return (
		<article aria-label="User question" style={cardStyle}>
			{question}
			<time style={timeStyle} dateTime={new Date(timestamp).toISOString()}>
				{time}
			</time>
		</article>
	);
}
