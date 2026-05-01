import { createTheme } from "@mantine/core";
import { colorTokens, radiusTokens, spaceTokens, typeTokens } from "./tokens";

export const theme = createTheme({
	fontFamily: typeTokens.fontFamily,
	primaryColor: "indigo",
	primaryShade: 6,
	colors: {
		indigo: colorTokens.brand,
		slate: colorTokens.neutral,
		success: colorTokens.success,
		warning: colorTokens.warning,
		danger: colorTokens.danger,
		info: colorTokens.info,
	},
	radius: {
		xs: radiusTokens.radius.xs,
		sm: radiusTokens.radius.sm,
		md: radiusTokens.radius.md,
		lg: radiusTokens.radius.lg,
		xl: radiusTokens.radius.xl,
	},
	defaultRadius: "md",
	spacing: {
		xs: spaceTokens.space.xs,
		sm: spaceTokens.space.sm,
		md: spaceTokens.space.md,
		lg: spaceTokens.space.lg,
		xl: spaceTokens.space.xl,
	},
	cursorType: "pointer",
});
