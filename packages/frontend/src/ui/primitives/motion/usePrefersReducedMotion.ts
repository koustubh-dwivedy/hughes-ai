import { useEffect, useState } from "react";

/**
 * Returns `true` when the user has requested reduced motion via the
 * `prefers-reduced-motion: reduce` media query. Components should
 * disable transitions / animations when this is true.
 */
export function usePrefersReducedMotion(): boolean {
	const [reduced, setReduced] = useState(() => {
		if (typeof window === "undefined" || !window.matchMedia) return false;
		return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
	});

	useEffect(() => {
		if (typeof window === "undefined" || !window.matchMedia) return;
		const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
		const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
		mql.addEventListener("change", handler);
		return () => mql.removeEventListener("change", handler);
	}, []);

	return reduced;
}

/**
 * Standard transition durations (ms) used across the app. Returns 0
 * when the user prefers reduced motion so components can skip the
 * animation entirely.
 */
export const motionDurations = {
	hoverLift: 80,
	routeFade: 150,
	countUp: 200,
	chartEntry: 350,
} as const;

export function getDuration(
	key: keyof typeof motionDurations,
	reduced: boolean,
): number {
	return reduced ? 0 : motionDurations[key];
}
