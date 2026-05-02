import { useEffect, useRef, useState } from "react";
import { colors, typography } from "../../../theme/tokens";

interface Props {
	text: string;
	durationMs?: number;
	onComplete?: () => void;
}

const cursorStyle: React.CSSProperties = {
	display: "inline-block",
	width: 2,
	height: "1em",
	background: colors.indigo[500],
	verticalAlign: "text-bottom",
	marginLeft: 2,
	animation: "stream-cursor-blink 1s step-end infinite",
};

const wrapperStyle: React.CSSProperties = {
	margin: 0,
	fontSize: typography.size.sm,
	color: colors.slate[800],
	lineHeight: 1.5,
	whiteSpace: "pre-wrap" as const,
};

const STEP_MS = 30;

export default function StreamingText({
	text,
	durationMs = 1500,
	onComplete,
}: Props) {
	const [shownLen, setShownLen] = useState(0);
	const [done, setDone] = useState(false);
	const completedRef = useRef(false);

	useEffect(() => {
		completedRef.current = false;
		setShownLen(0);
		setDone(false);
		if (text.length === 0) {
			completedRef.current = true;
			setDone(true);
			onComplete?.();
			return;
		}
		const startTime = Date.now();
		const id = window.setInterval(() => {
			const elapsed = Date.now() - startTime;
			const ratio = Math.min(1, elapsed / durationMs);
			const nextLen = Math.floor(text.length * ratio);
			setShownLen(nextLen);
			if (ratio >= 1 && !completedRef.current) {
				completedRef.current = true;
				window.clearInterval(id);
				setShownLen(text.length);
				setDone(true);
				onComplete?.();
			}
		}, STEP_MS);
		return () => window.clearInterval(id);
	}, [text, durationMs, onComplete]);

	return (
		<p
			aria-live="polite"
			aria-busy={!done}
			data-streaming={!done}
			style={wrapperStyle}
		>
			<style>{`
				@keyframes stream-cursor-blink {
					0%, 50% { opacity: 1; }
					50.01%, 100% { opacity: 0; }
				}
			`}</style>
			{text.slice(0, shownLen)}
			{!done && <span aria-hidden="true" style={cursorStyle} />}
		</p>
	);
}
