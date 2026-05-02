import type { AskResponse } from "../../shared/api/api";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import ResultPanel from "./ResultPanel";

interface Props {
	result: AskResponse;
	timestamp: number;
}

const cardStyle: React.CSSProperties = {
	alignSelf: "flex-start",
	maxWidth: "85%",
	padding: `${spacing[4]} ${spacing[6]}`,
	background: colors.white,
	color: colors.slate[800],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.lg,
	fontSize: typography.size.sm,
	lineHeight: 1.5,
};

const timeStyle: React.CSSProperties = {
	display: "block",
	marginTop: spacing[2],
	fontSize: typography.size.xs,
	color: colors.slate[400],
};

export default function AssistantMessage({ result, timestamp }: Props) {
	const time = new Date(timestamp).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
	return (
		<article aria-label="Assistant answer" style={cardStyle}>
			<ResultPanel result={result} />
			<time style={timeStyle} dateTime={new Date(timestamp).toISOString()}>
				{time}
			</time>
		</article>
	);
}
