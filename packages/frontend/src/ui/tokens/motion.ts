export const duration = {
	fast: "100ms",
	normal: "200ms",
	slow: "350ms",
} as const;

export const easing = {
	standard: "cubic-bezier(0.4, 0, 0.2, 1)",
	decelerate: "cubic-bezier(0, 0, 0.2, 1)",
	accelerate: "cubic-bezier(0.4, 0, 1, 1)",
} as const;
