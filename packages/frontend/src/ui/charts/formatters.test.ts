import { describe, expect, it } from "vitest";
import {
	formatAxisCurrency,
	formatAxisDate,
	formatAxisPercent,
} from "./formatters";

describe("formatAxisCurrency", () => {
	it.each([
		[0, "$0"],
		[1, "$1"],
		[499, "$499"],
		[500, "$500"],
		[999, "$999"],
		[1_000, "$1.0K"],
		[1_234, "$1.2K"],
		[9_999, "$10.0K"],
		[42_500, "$42.5K"],
		[999_000, "$999.0K"],
		[1_000_000, "$1.0M"],
		[42_500_000, "$42.5M"],
		[999_500_000, "$999.5M"],
		[1_000_000_000, "$1.0B"],
		[2_750_000_000, "$2.8B"],
	])("formats %d → %s", (input, expected) => {
		expect(formatAxisCurrency(input)).toBe(expected);
	});

	it.each([
		[-1_000, "-$1.0K"],
		[-42_500_000, "-$42.5M"],
	])("handles negative %d → %s", (input, expected) => {
		expect(formatAxisCurrency(input)).toBe(expected);
	});
});

describe("formatAxisPercent", () => {
	it.each([
		[0, "0.0%"],
		[0.5, "0.5%"],
		[1.0, "1.0%"],
		[3.8, "3.8%"],
		[5.0, "5.0%"],
		[12.34, "12.3%"],
		[50.0, "50.0%"],
		[100.0, "100.0%"],
		[-1.5, "-1.5%"],
	])("formats %d → %s", (input, expected) => {
		expect(formatAxisPercent(input)).toBe(expected);
	});
});

describe("formatAxisDate", () => {
	it.each([
		["2025-01", "Jan '25"],
		["2025-02", "Feb '25"],
		["2025-03", "Mar '25"],
		["2025-04", "Apr '25"],
		["2025-05", "May '25"],
		["2025-06", "Jun '25"],
		["2025-07", "Jul '25"],
		["2025-08", "Aug '25"],
		["2025-09", "Sep '25"],
		["2025-10", "Oct '25"],
		["2025-11", "Nov '25"],
		["2025-12", "Dec '25"],
		["2026-01", "Jan '26"],
		["2024-06", "Jun '24"],
		["2025-04-30", "Apr '25"],
	])("formats %s → %s", (input, expected) => {
		expect(formatAxisDate(input)).toBe(expected);
	});

	it("returns input unchanged for unrecognised format", () => {
		expect(formatAxisDate("invalid")).toBe("invalid");
	});
});
