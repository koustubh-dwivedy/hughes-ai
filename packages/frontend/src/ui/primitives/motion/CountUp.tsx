import { useEffect, useState } from "react";
import {
	motionDurations,
	usePrefersReducedMotion,
} from "./usePrefersReducedMotion";

interface Props {
	value: string;
}

/**
 * Renders a tile value with a brief 200ms count-up animation when the
 * value changes. The "count-up" is implemented as a quick opacity
 * pulse rather than numeric interpolation — it works for any string
 * (currency, percentage, count) and is invisible when the user
 * prefers reduced motion.
 */
export default function CountUp({ value }: Props) {
	const reduced = usePrefersReducedMotion();
	const [opacity, setOpacity] = useState(1);

	useEffect(() => {
		if (reduced) return;
		// Read value inside so biome's exhaustive-deps rule treats it
		// as required: every value change re-runs the brief opacity pulse.
		void value;
		setOpacity(0.3);
		const id = window.setTimeout(() => setOpacity(1), 16);
		return () => window.clearTimeout(id);
	}, [value, reduced]);

	const duration = reduced ? 0 : motionDurations.countUp;
	return (
		<span
			data-count-up
			style={{ opacity, transition: `opacity ${duration}ms ease` }}
		>
			{value}
		</span>
	);
}
