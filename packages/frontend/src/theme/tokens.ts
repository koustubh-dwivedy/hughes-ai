export const colors = {
	slate: {
		50: "#f8fafc",
		100: "#f1f5f9",
		200: "#e2e8f0",
		300: "#cbd5e1",
		400: "#94a3b8",
		500: "#64748b",
		600: "#475569",
		700: "#334155",
		800: "#1e293b",
		900: "#0f172a",
	},
	indigo: {
		50: "#eef2ff",
		100: "#e0e7ff",
		500: "#6366f1",
		600: "#4f46e5",
		700: "#4338ca",
	},
	white: "#ffffff",
} as const;

export const spacing = {
	1: "0.25rem",
	2: "0.5rem",
	3: "0.75rem",
	4: "1rem",
	6: "1.5rem",
	8: "2rem",
	12: "3rem",
} as const;

export const typography = {
	fontFamily: '"Inter", system-ui, sans-serif',
	size: {
		xs: "0.75rem",
		sm: "0.875rem",
		base: "1rem",
		lg: "1.125rem",
		xl: "1.25rem",
		"2xl": "1.5rem",
	},
	weight: {
		normal: 400,
		medium: 500,
		semibold: 600,
		bold: 700,
	},
} as const;

export const radii = {
	sm: "0.25rem",
	md: "0.375rem",
	lg: "0.5rem",
	xl: "0.75rem",
} as const;
