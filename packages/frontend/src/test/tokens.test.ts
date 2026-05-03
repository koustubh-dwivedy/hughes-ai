import { describe, expect, it } from "vitest";
import { colors, radii, spacing, typography } from "../theme/tokens";

describe("tokens", () => {
	it("colors.slate has all 10 shades", () => {
		const keys = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900] as const;
		for (const k of keys) {
			expect(colors.slate[k]).toMatch(/^#[0-9a-f]{6}$/);
		}
	});

	it("colors.indigo has expected monochrome shades", () => {
		expect(colors.indigo[50]).toBe("#fafafa");
		expect(colors.indigo[500]).toBe("#737373");
		expect(colors.indigo[700]).toBe("#262626");
	});

	it("colors.white is white", () => {
		expect(colors.white).toBe("#ffffff");
	});

	it("spacing[4] is 1rem", () => {
		expect(spacing[4]).toBe("1rem");
	});

	it("spacing has all expected keys", () => {
		const keys = [1, 2, 3, 4, 6, 8, 12] as const;
		for (const k of keys) {
			expect(spacing[k]).toMatch(/rem$/);
		}
	});

	it("typography.fontFamily includes Inter", () => {
		expect(typography.fontFamily).toContain("Inter");
	});

	it("typography.size has all 6 steps", () => {
		const keys = ["xs", "sm", "base", "lg", "xl", "2xl"] as const;
		for (const k of keys) {
			expect(typography.size[k]).toMatch(/rem$/);
		}
	});

	it("typography.weight has all 4 steps", () => {
		expect(typography.weight.normal).toBe(400);
		expect(typography.weight.medium).toBe(500);
		expect(typography.weight.semibold).toBe(600);
		expect(typography.weight.bold).toBe(700);
	});

	it("radii has all 4 keys", () => {
		const keys = ["sm", "md", "lg", "xl"] as const;
		for (const k of keys) {
			expect(radii[k]).toMatch(/rem$/);
		}
	});
});
