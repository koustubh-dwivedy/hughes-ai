import type { CSSVariablesResolver } from "@mantine/core";
import * as colorTokens from "./color";
import { elevation } from "./elevation";
import { duration } from "./motion";
import { zIndex } from "./z";

export * as colorTokens from "./color";
export * as elevationTokens from "./elevation";
export * as motionTokens from "./motion";
export * as radiusTokens from "./radius";
export * as spaceTokens from "./space";
export * as typeTokens from "./type";
export * as zTokens from "./z";

export const cssVariablesResolver: CSSVariablesResolver = (_theme) => ({
	variables: {
		"--hughes-color-success": colorTokens.success[5],
		"--hughes-color-warning": colorTokens.warning[5],
		"--hughes-color-danger": colorTokens.danger[5],
		"--hughes-color-info": colorTokens.info[5],
		"--hughes-motion-fast": duration.fast,
		"--hughes-motion-normal": duration.normal,
		"--hughes-motion-slow": duration.slow,
		"--hughes-shadow-sm": elevation.sm,
		"--hughes-shadow-md": elevation.md,
		"--hughes-z-modal": String(zIndex.modal),
		"--hughes-z-toast": String(zIndex.toast),
	},
	dark: {},
	light: {},
});
