import { useState } from "react";
import type { AskResponse } from "../../shared/api/api";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import ResultPanel from "./ResultPanel";
import StreamingText from "./messages/StreamingText";

interface Props {
	result: AskResponse;
	timestamp: number;
	streaming?: boolean;
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

export default function AssistantMessage({
	result,
	timestamp,
	streaming = true,
}: Props) {
	const [streamDone, setStreamDone] = useState(!streaming);
	const time = new Date(timestamp).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
	const showStream =
		streaming &&
		!streamDone &&
		result.explanation !== null &&
		result.explanation.length > 0;

	return (
		<article aria-label="Assistant answer" style={cardStyle}>
			{showStream && result.explanation !== null ? (
				<StreamingText
					text={result.explanation}
					onComplete={() => setStreamDone(true)}
				/>
			) : (
				<ResultPanel result={result} />
			)}
			<time style={timeStyle} dateTime={new Date(timestamp).toISOString()}>
				{time}
			</time>
		</article>
	);
}
