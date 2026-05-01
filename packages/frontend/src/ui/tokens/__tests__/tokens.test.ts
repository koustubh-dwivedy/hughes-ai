import type { MantineTheme } from "@mantine/core";
import { describe, expect, it } from "vitest";
import {
	colorTokens,
	cssVariablesResolver,
	elevationTokens,
	motionTokens,
	radiusTokens,
	spaceTokens,
	typeTokens,
	zTokens,
} from "..";

const hexPattern = /^#[0-9a-f]{6}$/i;

// The resolver ignores the theme argument; cast to avoid full MantineTheme construction.
const fakeTheme = {} as MantineTheme;
const resolved = cssVariablesResolver(fakeTheme);
const vars = resolved.variables as Record<string, string>;

describe("color tokens", () => {
	const palettes = [
		"brand",
		"neutral",
		"success",
		"warning",
		"danger",
		"info",
	] as const;

	it.each(palettes)("%s has exactly 10 hex shades", (name) => {
		const shades = colorTokens[name];
		expect(shades).toHaveLength(10);
		for (const shade of shades) {
			expect(shade).toMatch(hexPattern);
		}
	});

	it("brand shade 6 is the primary indigo", () => {
		expect(colorTokens.brand[6]).toBe("#4f46e5");
	});

	it("success base shade is a hex color", () => {
		expect(colorTokens.success[5]).toMatch(hexPattern);
	});

	it("white is #ffffff", () => {
		expect(colorTokens.white).toBe("#ffffff");
	});
});

describe("space tokens", () => {
	it("named scale has xs through 2xl", () => {
		const keys = ["xs", "sm", "md", "lg", "xl", "2xl"] as const;
		for (const k of keys) {
			expect(spaceTokens.space[k]).toMatch(/rem$/);
		}
	});

	it("numeric scale has backward-compat keys", () => {
		const keys = [1, 2, 3, 4, 6, 8, 12] as const;
		for (const k of keys) {
			expect(spaceTokens.spaceScale[k]).toMatch(/rem$/);
		}
	});

	it("md is 1rem", () => {
		expect(spaceTokens.space.md).toBe("1rem");
	});
});

describe("type tokens", () => {
	it("fontFamily includes Inter", () => {
		expect(typeTokens.fontFamily).toContain("Inter");
	});

	it("fontSize has 6 steps all in rem", () => {
		const keys = ["xs", "sm", "md", "lg", "xl", "2xl"] as const;
		for (const k of keys) {
			expect(typeTokens.fontSize[k]).toMatch(/rem$/);
		}
	});

	it("fontWeight has 4 steps", () => {
		expect(typeTokens.fontWeight.normal).toBe(400);
		expect(typeTokens.fontWeight.medium).toBe(500);
		expect(typeTokens.fontWeight.semibold).toBe(600);
		expect(typeTokens.fontWeight.bold).toBe(700);
	});

	it("lineHeight increases from tight to relaxed", () => {
		const parse = (s: string) => Number(s);
		expect(parse(typeTokens.lineHeight.tight)).toBeLessThan(
			parse(typeTokens.lineHeight.base),
		);
		expect(parse(typeTokens.lineHeight.base)).toBeLessThan(
			parse(typeTokens.lineHeight.relaxed),
		);
	});
});

describe("motion tokens", () => {
	it("durations ascend fast < normal < slow", () => {
		const parse = (s: string) => Number.parseInt(s, 10);
		expect(parse(motionTokens.duration.fast)).toBeLessThan(
			parse(motionTokens.duration.normal),
		);
		expect(parse(motionTokens.duration.normal)).toBeLessThan(
			parse(motionTokens.duration.slow),
		);
	});

	it("easings are cubic-bezier strings", () => {
		for (const val of Object.values(motionTokens.easing)) {
			expect(val).toContain("cubic-bezier");
		}
	});
});

describe("elevation tokens", () => {
	it("has 6 steps including none", () => {
		const keys = ["none", "xs", "sm", "md", "lg", "xl"] as const;
		for (const k of keys) {
			expect(elevationTokens.elevation[k]).toBeTruthy();
		}
	});

	it("none is the string 'none'", () => {
		expect(elevationTokens.elevation.none).toBe("none");
	});

	it("non-none shadows contain rgb", () => {
		for (const [k, v] of Object.entries(elevationTokens.elevation)) {
			if (k !== "none") expect(v).toContain("rgb");
		}
	});
});

describe("radius tokens", () => {
	it("has xs through full", () => {
		const keys = ["xs", "sm", "md", "lg", "xl", "full"] as const;
		for (const k of keys) {
			expect(radiusTokens.radius[k]).toBeTruthy();
		}
	});

	it("full is 9999px", () => {
		expect(radiusTokens.radius.full).toBe("9999px");
	});
});

describe("z-index tokens", () => {
	it("layers are strictly ascending", () => {
		const { base, above, dropdown, sticky, overlay, modal, toast } =
			zTokens.zIndex;
		expect(base).toBeLessThan(above);
		expect(above).toBeLessThan(dropdown);
		expect(dropdown).toBeLessThan(sticky);
		expect(sticky).toBeLessThan(overlay);
		expect(overlay).toBeLessThan(modal);
		expect(modal).toBeLessThan(toast);
	});
});

describe("cssVariablesResolver", () => {
	it("returns variables, dark, light keys", () => {
		expect(resolved).toHaveProperty("variables");
		expect(resolved).toHaveProperty("dark");
		expect(resolved).toHaveProperty("light");
	});

	it("semantic color variables are hex strings", () => {
		for (const key of [
			"--hughes-color-success",
			"--hughes-color-warning",
			"--hughes-color-danger",
			"--hughes-color-info",
		]) {
			expect(vars[key]).toMatch(hexPattern);
		}
	});

	it("motion variables match duration tokens", () => {
		expect(vars["--hughes-motion-fast"]).toBe("100ms");
		expect(vars["--hughes-motion-normal"]).toBe("200ms");
		expect(vars["--hughes-motion-slow"]).toBe("350ms");
	});

	it("shadow variables contain rgb", () => {
		expect(vars["--hughes-shadow-sm"]).toContain("rgb");
		expect(vars["--hughes-shadow-md"]).toContain("rgb");
	});

	it("z-index variables are numeric strings", () => {
		expect(Number(vars["--hughes-z-modal"])).toBe(400);
		expect(Number(vars["--hughes-z-toast"])).toBe(500);
	});
});
