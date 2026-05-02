/**
 * HUG-152: parametric coverage table for the format helpers. Every
 * audit bug we've ever fixed in dashboards is captured as a
 * permanent regression row so it can never silently come back.
 *
 * Audit bugs explicitly covered:
 *   - "$-0.2M"          → sign placement, must produce "-$0.2M"
 *   - "↓ 237659.38"     → raw number leaked into delta, must format
 *   - "0.0M"            → trailing zero on million boundary
 *   - "0.032"           → raw decimal leaked instead of "3.2%"
 */

import { describe, expect, it } from "vitest";
import { formatCurrency, formatDelta, formatPercent } from "../format";

interface Row<Args extends unknown[]> {
	name: string;
	args: Args;
	expected: string;
}

const CURRENCY: Array<Row<[number]>> = [
	// Whole-millions and above
	{ name: "exactly 1M", args: [1_000_000], expected: "$1M" },
	{ name: "42.5M", args: [42_500_000], expected: "$42.5M" },
	{ name: "142.5M", args: [142_500_000], expected: "$142.5M" },
	{ name: "1B as 1000M", args: [1_000_000_000], expected: "$1000M" },
	// Thousands
	{ name: "exactly 1K", args: [1_000], expected: "$1K" },
	{ name: "142.5K", args: [142_500], expected: "$142.5K" },
	{ name: "999K stays K", args: [999_000], expected: "$999K" },
	{ name: "999.9K rounds to 999.9K", args: [999_900], expected: "$999.9K" },
	// Sub-thousand
	{ name: "$142", args: [142], expected: "$142" },
	{ name: "$0", args: [0], expected: "$0" },
	{ name: "$1", args: [1], expected: "$1" },
	{ name: "rounds 99.7 → $100", args: [99.7], expected: "$100" },
	{ name: "rounds 99.4 → $99", args: [99.4], expected: "$99" },
	// AUDIT BUG: sign placement
	{
		name: "audit: -1.2M as -$1.2M not $-1.2M",
		args: [-1_200_000],
		expected: "-$1.2M",
	},
	{
		name: "audit: -500K as -$500K not $-500K",
		args: [-500_000],
		expected: "-$500K",
	},
	{
		name: "audit: -200K as -$0.2M when ≥1M magnitude does NOT happen here",
		args: [-200_000],
		expected: "-$200K",
	},
	{ name: "audit: -99 as -$99 not $-99", args: [-99], expected: "-$99" },
	// AUDIT BUG: trailing zeros stripped (0.0M → $0)
	{ name: "audit: 0 → $0 not $0.0M", args: [0], expected: "$0" },
	{ name: "audit: -0 normalised to $0", args: [-0], expected: "$0" },
	// Unit boundaries
	{ name: "999.999.99 stays K not M", args: [999_999.99], expected: "$1000K" },
	{ name: "1.05M trims to 1.1M", args: [1_050_000], expected: "$1.1M" },
];

const PERCENT: Array<Row<[number, number?]>> = [
	// AUDIT BUG: raw decimal leaked (0.032 must become 3.2%)
	{ name: "audit: 0.032 → 3.2%", args: [0.032], expected: "3.2%" },
	{ name: "audit: 0.913 → 91.3%", args: [0.913], expected: "91.3%" },
	{ name: "0 → 0.0%", args: [0], expected: "0.0%" },
	{ name: "1 → 100.0%", args: [1], expected: "100.0%" },
	{ name: "0.0001 → 0.0%", args: [0.0001], expected: "0.0%" },
	{ name: "0.00001 → 0.0%", args: [0.00001], expected: "0.0%" },
	{ name: "negative -0.04 → -4.0%", args: [-0.04], expected: "-4.0%" },
	{ name: "decimals=2 → 12.35%", args: [0.12345, 2], expected: "12.35%" },
	{ name: "decimals=0 → 12%", args: [0.12345, 0], expected: "12%" },
	{ name: "decimals=3 → 12.345%", args: [0.12345, 3], expected: "12.345%" },
	{ name: "round-up boundary 0.005 → 0.5%", args: [0.005], expected: "0.5%" },
];

const DELTA: Array<Row<[number, number?]>> = [
	// AUDIT BUG: raw number leaked (must become formatted delta)
	{ name: "audit: positive ↑ 4.2%", args: [4.2], expected: "↑ 4.2%" },
	{ name: "audit: negative ↓ 1.8%", args: [-1.8], expected: "↓ 1.8%" },
	{ name: "audit: zero → em dash", args: [0], expected: "—" },
	{ name: "small positive 0.1", args: [0.1], expected: "↑ 0.1%" },
	{ name: "small negative -0.1", args: [-0.1], expected: "↓ 0.1%" },
	{ name: "decimals=2 positive", args: [3.567, 2], expected: "↑ 3.57%" },
	{ name: "decimals=2 negative", args: [-2.345, 2], expected: "↓ 2.35%" },
	{ name: "decimals=0 truncates", args: [4.7, 0], expected: "↑ 5%" },
	{ name: "exactly 100", args: [100], expected: "↑ 100.0%" },
	{ name: "exactly -100", args: [-100], expected: "↓ 100.0%" },
];

describe("formatCurrency — parametric audit table", () => {
	it.each(CURRENCY)("$name → $expected", ({ args, expected }) => {
		expect(formatCurrency(...args)).toBe(expected);
	});

	it("never produces a $- prefix on negatives (sign goes before $)", () => {
		for (const sample of [-1, -99, -1_000, -1_500_000, -42_750_000]) {
			expect(formatCurrency(sample)).not.toContain("$-");
		}
	});

	it("never produces a stale .0 trailing fraction on whole units", () => {
		for (const sample of [1_000_000, 2_000_000, 5_000, 10_000]) {
			expect(formatCurrency(sample)).not.toMatch(/\.0[A-Z]?$/);
		}
	});
});

describe("formatPercent — parametric audit table", () => {
	it.each(PERCENT)("$name → $expected", ({ args, expected }) => {
		expect(formatPercent(...args)).toBe(expected);
	});

	it("never returns a bare decimal — always has %", () => {
		for (const sample of [0, 0.001, 0.5, 1, 2.5]) {
			expect(formatPercent(sample)).toMatch(/%$/);
		}
	});
});

describe("formatDelta — parametric audit table", () => {
	it.each(DELTA)("$name → $expected", ({ args, expected }) => {
		expect(formatDelta(...args)).toBe(expected);
	});

	it("never leaks a raw number — every non-zero result has an arrow", () => {
		for (const sample of [1, -1, 0.5, -0.5, 50, -50]) {
			const out = formatDelta(sample);
			expect(out).toMatch(/^[↑↓]\s/);
		}
	});

	it("zero is the only value that returns the em dash", () => {
		expect(formatDelta(0)).toBe("—");
		for (const sample of [0.0001, -0.0001, 1, -1]) {
			expect(formatDelta(sample)).not.toBe("—");
		}
	});
});

describe("Coverage discipline", () => {
	it("audits the table size to keep ≥40 parametric rows (HUG-152 floor)", () => {
		expect(
			CURRENCY.length + PERCENT.length + DELTA.length,
		).toBeGreaterThanOrEqual(40);
	});
});
