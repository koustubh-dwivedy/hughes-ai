/**
 * Live "agent is working" bubble (HUG-201, A+B+C from the feedback bundle).
 *
 * Renders an assistant-styled bubble while a turn is streaming. Embeds
 * the StepIndicator so the user sees tool-call progress (Looking up
 * metrics… → Querying MetricFlow… → Drafting the answer…) inline rather
 * than as a separate footer block. A trio of pulsing dots gives a
 * passive "still working" cue when the stream has started but no step
 * events have arrived yet.
 */

import { useAppSelector } from "../../../shared/api/hooks";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import StepIndicator from "./StepIndicator";

const bubbleStyle: React.CSSProperties = {
	alignSelf: "flex-start",
	maxWidth: "92%",
	background: colors.slate[50],
	color: colors.slate[800],
	padding: spacing[3],
	borderRadius: radii.lg,
	border: `1px solid ${colors.slate[200]}`,
	fontSize: typography.size.sm,
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
};

const pulseRowStyle: React.CSSProperties = {
	display: "inline-flex",
	gap: 6,
	alignItems: "center",
	color: colors.slate[600],
	fontStyle: "italic",
};

const dotBaseStyle: React.CSSProperties = {
	display: "inline-block",
	width: 7,
	height: 7,
	borderRadius: "50%",
	background: colors.slate[500],
	animation: "hughesThinkingDot 1.2s ease-in-out infinite",
};

const KEYFRAMES_ID = "hughes-thinking-keyframes";

function ensureKeyframes(): void {
	if (typeof document === "undefined") return;
	if (document.getElementById(KEYFRAMES_ID)) return;
	const style = document.createElement("style");
	style.id = KEYFRAMES_ID;
	style.textContent = `
@keyframes hughesThinkingDot {
  0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-2px); }
}
`;
	document.head.appendChild(style);
}

export default function ThinkingBubble() {
	const streaming = useAppSelector((s) => s.thread.streaming);
	const steps = useAppSelector((s) => s.thread.steps);
	if (!streaming) return null;
	ensureKeyframes();
	return (
		<article
			aria-label="Assistant is thinking"
			aria-live="polite"
			style={bubbleStyle}
		>
			<span style={pulseRowStyle}>
				<span style={{ ...dotBaseStyle, animationDelay: "0s" }} aria-hidden />
				<span style={{ ...dotBaseStyle, animationDelay: "0.15s" }} aria-hidden />
				<span style={{ ...dotBaseStyle, animationDelay: "0.3s" }} aria-hidden />
				<span style={{ marginLeft: spacing[2] }}>
					{steps.length === 0 ? "Thinking…" : "Working on your answer…"}
				</span>
			</span>
			<StepIndicator />
		</article>
	);
}
