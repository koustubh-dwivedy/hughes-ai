type Shade = readonly [
	string,
	string,
	string,
	string,
	string,
	string,
	string,
	string,
	string,
	string,
];

// Brand palette is intentionally a neutral gray ramp: the product wordmark
// is monochrome (logo PNG) and the rest of the chrome should follow. Using
// a grayscale ramp keeps Mantine's primary color machinery (filled/light/
// hover variants) producing readable on-page accents without any purple.
export const brand: Shade = [
	"#fafafa", // 0 → 50
	"#f5f5f5", // 1 → 100
	"#e5e5e5", // 2 → 200
	"#d4d4d4", // 3 → 300
	"#a3a3a3", // 4 → 400
	"#737373", // 5 → 500
	"#404040", // 6 → 600 (primary)
	"#262626", // 7 → 700
	"#171717", // 8 → 800
	"#0a0a0a", // 9 → 900
];

export const neutral: Shade = [
	"#f8fafc", // 0 → 50
	"#f1f5f9", // 1 → 100
	"#e2e8f0", // 2 → 200
	"#cbd5e1", // 3 → 300
	"#94a3b8", // 4 → 400
	"#64748b", // 5 → 500
	"#475569", // 6 → 600
	"#334155", // 7 → 700
	"#1e293b", // 8 → 800
	"#0f172a", // 9 → 900
];

export const success: Shade = [
	"#f0fdf4", // 0
	"#dcfce7", // 1
	"#bbf7d0", // 2
	"#86efac", // 3
	"#4ade80", // 4
	"#22c55e", // 5 (base)
	"#16a34a", // 6
	"#15803d", // 7
	"#166534", // 8
	"#14532d", // 9
];

export const warning: Shade = [
	"#fffbeb", // 0
	"#fef3c7", // 1
	"#fde68a", // 2
	"#fcd34d", // 3
	"#fbbf24", // 4
	"#f59e0b", // 5 (base)
	"#d97706", // 6
	"#b45309", // 7
	"#92400e", // 8
	"#78350f", // 9
];

export const danger: Shade = [
	"#fff1f2", // 0
	"#ffe4e6", // 1
	"#fecdd3", // 2
	"#fda4af", // 3
	"#fb7185", // 4
	"#f43f5e", // 5 (base)
	"#e11d48", // 6
	"#be123c", // 7
	"#9f1239", // 8
	"#881337", // 9
];

export const info: Shade = [
	"#f0f9ff", // 0
	"#e0f2fe", // 1
	"#bae6fd", // 2
	"#7dd3fc", // 3
	"#38bdf8", // 4
	"#0ea5e9", // 5 (base)
	"#0284c7", // 6
	"#0369a1", // 7
	"#075985", // 8
	"#0c4a6e", // 9
];

export const white = "#ffffff";
