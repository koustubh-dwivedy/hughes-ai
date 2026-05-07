/**
 * Live "Thinking" rolling-line bubble (HUG-202 Phase 1).
 *
 * Single line of narration that updates in place as the agent works.
 * The line replaces the previous one with a brief cross-fade — the
 * screen never accumulates a multi-line list. Three pulsing dots
 * give a passive "still working" signal between updates.
 *
 * The full ordered trace lives in the References modal once the turn
 * completes; this bubble is a UX layer, not the audit layer.
 */

import { useEffect, useRef, useState } from "react";
import { useAppSelector } from "../../../shared/api/hooks";
import { colors, radii, spacing, typography } from "../../../theme/tokens";

const DEFAULT_LINE = "Thinking…";

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
	alignItems: "center",
	gap: spacing[2],
};

const dotsStyle: React.CSSProperties = {
	display: "inline-flex",
	gap: 6,
	alignItems: "center",
};

const dotBaseStyle: React.CSSProperties = {
	display: "inline-block",
	width: 7,
	height: 7,
	borderRadius: "50%",
	background: colors.slate[500],
	animation: "hughesThinkingDot 1.2s ease-in-out infinite",
};

const lineWrapStyle: React.CSSProperties = {
	flex: 1,
	color: colors.slate[700],
	fontStyle: "italic",
	overflow: "hidden",
	textOverflow: "ellipsis",
	whiteSpace: "nowrap",
	transition: "opacity 180ms ease",
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
	const narration = useAppSelector((s) => s.thread.narrationLine);
	const visibleLine = narration ?? DEFAULT_LINE;
	const [displayLine, setDisplayLine] = useState(visibleLine);
	const [opacity, setOpacity] = useState(1);
	const lastLineRef = useRef(visibleLine);

	useEffect(() => {
		if (visibleLine === lastLineRef.current) return;
		// Cross-fade: dim, swap, fade back in.
		setOpacity(0);
		const swap = window.setTimeout(() => {
			setDisplayLine(visibleLine);
			lastLineRef.current = visibleLine;
			setOpacity(1);
		}, 180);
		return () => window.clearTimeout(swap);
	}, [visibleLine]);

	if (!streaming) return null;
	ensureKeyframes();
	return (
		<article
			aria-label="Assistant is thinking"
			aria-live="polite"
			style={bubbleStyle}
		>
			<span style={dotsStyle}>
				<span style={{ ...dotBaseStyle, animationDelay: "0s" }} aria-hidden />
				<span style={{ ...dotBaseStyle, animationDelay: "0.15s" }} aria-hidden />
				<span style={{ ...dotBaseStyle, animationDelay: "0.3s" }} aria-hidden />
			</span>
			<span
				data-testid="thinking-line"
				style={{ ...lineWrapStyle, opacity }}
			>
				{displayLine}
			</span>
		</article>
	);
}
