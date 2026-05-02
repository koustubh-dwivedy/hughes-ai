import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
	getDuration,
	usePrefersReducedMotion,
} from "./usePrefersReducedMotion";

interface Props {
	children: React.ReactNode;
}

/**
 * Cross-fades the routed content on every pathname change. Renders
 * the children directly with no animation when the user prefers
 * reduced motion.
 */
export default function RouteFade({ children }: Props) {
	const reduced = usePrefersReducedMotion();
	const { pathname } = useLocation();
	const [opacity, setOpacity] = useState(1);
	const duration = getDuration("routeFade", reduced);

	useEffect(() => {
		if (reduced) return;
		// Read pathname inside so biome's exhaustive-deps rule treats it
		// as required: every pathname change re-runs the fade-out → fade-in.
		void pathname;
		setOpacity(0);
		const id = window.setTimeout(() => setOpacity(1), 0);
		return () => window.clearTimeout(id);
	}, [pathname, reduced]);

	return (
		<div
			data-route-fade
			style={{ opacity, transition: `opacity ${duration}ms ease` }}
		>
			{children}
		</div>
	);
}
