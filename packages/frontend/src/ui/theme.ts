import { createTheme } from "@mantine/core";
import { radii, spacing, typography } from "../theme/tokens";

const indigoShades: [
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
] = [
	"#eef2ff", // 0 → 50
	"#e0e7ff", // 1 → 100
	"#c7d2fe", // 2 → 200
	"#a5b4fc", // 3 → 300
	"#818cf8", // 4 → 400
	"#6366f1", // 5 → 500
	"#4f46e5", // 6 → 600
	"#4338ca", // 7 → 700
	"#3730a3", // 8 → 800
	"#312e81", // 9 → 900
];

const slateShades: [
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
] = [
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

export const theme = createTheme({
	fontFamily: typography.fontFamily,
	primaryColor: "indigo",
	primaryShade: 6,
	colors: {
		indigo: indigoShades,
		slate: slateShades,
	},
	radius: {
		sm: radii.sm,
		md: radii.md,
		lg: radii.lg,
		xl: radii.xl,
	},
	defaultRadius: "md",
	spacing: {
		xs: spacing[2],
		sm: spacing[3],
		md: spacing[4],
		lg: spacing[6],
		xl: spacing[8],
	},
	cursorType: "pointer",
});
