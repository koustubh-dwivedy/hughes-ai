/**
 * Reveal a string one character at a time (HUG-201, option E).
 *
 * Used for the assistant's summary on the FIRST render after a final
 * SSE event lands. The full text is already in memory; the typewriter
 * is purely a presentation animation that gives the answer a sense of
 * arrival rather than appearing atomically. Honors
 * `prefers-reduced-motion`: when set, the full text shows immediately.
 */

import { useEffect, useRef, useState } from "react";
import { usePrefersReducedMotion } from "../../../ui/primitives/motion/usePrefersReducedMotion";

interface Props {
	text: string;
	/** ms per character. Default ~20 (50 chars / sec). */
	speedMs?: number;
}

const DEFAULT_SPEED_MS = 18;

export default function TypewriterText({ text, speedMs = DEFAULT_SPEED_MS }: Props) {
	const reduced = usePrefersReducedMotion();
	const [revealed, setRevealed] = useState(reduced ? text.length : 0);
	const idxRef = useRef(0);

	useEffect(() => {
		// New text content → restart the reveal.
		idxRef.current = 0;
		setRevealed(reduced ? text.length : 0);
		if (reduced || text.length === 0) return;
		const handle = window.setInterval(() => {
			idxRef.current += 1;
			if (idxRef.current >= text.length) {
				setRevealed(text.length);
				window.clearInterval(handle);
				return;
			}
			setRevealed(idxRef.current);
		}, speedMs);
		return () => window.clearInterval(handle);
	}, [text, speedMs, reduced]);

	return <>{text.slice(0, revealed)}</>;
}
