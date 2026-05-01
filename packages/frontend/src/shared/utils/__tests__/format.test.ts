import { describe, expect, it } from "vitest";
import { formatCurrency, formatDelta, formatPercent } from "../format";

describe("formatCurrency", () => {
	it("formats millions with M suffix", () => {
		expect(formatCurrency(42_500_000)).toBe("$42.5M");
	});

	it("formats exactly 1 million", () => {
		expect(formatCurrency(1_000_000)).toBe("$1M");
	});

	it("formats large millions", () => {
		expect(formatCurrency(142_500_000)).toBe("$142.5M");
	});

	it("formats thousands with K suffix", () => {
		expect(formatCurrency(142_500)).toBe("$142.5K");
	});

	it("formats exactly 1 thousand", () => {
		expect(formatCurrency(1_000)).toBe("$1K");
	});

	it("formats sub-thousand as whole dollars", () => {
		expect(formatCurrency(142)).toBe("$142");
	});

	it("formats zero", () => {
		expect(formatCurrency(0)).toBe("$0");
	});

	it("formats negative millions correctly (sign before $)", () => {
		const result = formatCurrency(-1_200_000);
		expect(result).toBe("-$1.2M");
		expect(result).not.toContain("$-");
	});

	it("formats negative thousands correctly (sign before $)", () => {
		const result = formatCurrency(-500_000);
		expect(result).toBe("-$500K");
		expect(result).not.toContain("$-");
	});

	it("formats negative sub-thousand correctly", () => {
		const result = formatCurrency(-99);
		expect(result).toBe("-$99");
		expect(result).not.toContain("$-");
	});

	it("rounds sub-thousand values", () => {
		expect(formatCurrency(99.7)).toBe("$100");
	});
});

describe("formatPercent", () => {
	it("converts ratio to percent with default 1 decimal", () => {
		expect(formatPercent(0.032)).toBe("3.2%");
	});

	it("converts large ratio to percent", () => {
		expect(formatPercent(0.913)).toBe("91.3%");
	});

	it("formats zero percent", () => {
		expect(formatPercent(0)).toBe("0.0%");
	});

	it("formats 100 percent", () => {
		expect(formatPercent(1)).toBe("100.0%");
	});

	it("respects decimals parameter", () => {
		expect(formatPercent(0.12345, 2)).toBe("12.35%");
	});
});

describe("formatDelta", () => {
	it("formats positive delta with up arrow", () => {
		expect(formatDelta(4.2)).toBe("↑ 4.2%");
	});

	it("formats negative delta with down arrow", () => {
		expect(formatDelta(-1.8)).toBe("↓ 1.8%");
	});

	it("formats zero as em dash", () => {
		expect(formatDelta(0)).toBe("—");
	});

	it("respects decimals parameter for positive", () => {
		expect(formatDelta(3.567, 2)).toBe("↑ 3.57%");
	});

	it("respects decimals parameter for negative", () => {
		expect(formatDelta(-2.345, 2)).toBe("↓ 2.35%");
	});

	it("formats small positive delta", () => {
		expect(formatDelta(0.1)).toBe("↑ 0.1%");
	});

	it("formats small negative delta", () => {
		expect(formatDelta(-0.1)).toBe("↓ 0.1%");
	});
});
