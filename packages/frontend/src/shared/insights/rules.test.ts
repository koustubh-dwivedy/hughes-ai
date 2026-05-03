import { describe, expect, it } from "vitest";
import {
	changeByProductInsight,
	depositMixInsight,
	loanRateSpreadInsight,
	officerLoadInsight,
	pastDueTrendInsight,
	ratioTrendInsight,
	watchlistTrendInsight,
} from "./rules";

describe("pastDueTrendInsight", () => {
	it("flags a 10% MoM rise as warn", () => {
		const out = pastDueTrendInsight([
			{ period: "Jan", "30-59": 80, "60-89": 15, "90+": 5 },
			{ period: "Feb", "30-59": 90, "60-89": 16, "90+": 5 },
		]);
		expect(out.tone).toBe("warn");
		expect(out.bullets.join(" ")).toMatch(/rose/);
	});

	it("calls a 10% MoM drop a success", () => {
		const out = pastDueTrendInsight([
			{ period: "Jan", "30-59": 100, "60-89": 20, "90+": 10 },
			{ period: "Feb", "30-59": 80, "60-89": 18, "90+": 10 },
		]);
		expect(out.tone).toBe("success");
	});

	it("returns neutral with too few points", () => {
		expect(pastDueTrendInsight([]).bullets).toHaveLength(0);
	});
});

describe("ratioTrendInsight", () => {
	it("calls last value under 1.5% a success", () => {
		const out = ratioTrendInsight([
			{ period: "Jan", value: 1.2 },
			{ period: "Feb", value: 1.0 },
		]);
		expect(out.tone).toBe("success");
	});

	it("warns when ratio crosses 2.5%", () => {
		const out = ratioTrendInsight([
			{ period: "Jan", value: 2.0 },
			{ period: "Feb", value: 2.6 },
		]);
		expect(out.tone).toBe("warn");
	});
});

describe("depositMixInsight", () => {
	it("warns when one product is over 50%", () => {
		const out = depositMixInsight([
			{ label: "Checking", value: 60 },
			{ label: "Savings", value: 30 },
			{ label: "CDs", value: 10 },
		]);
		expect(out.tone).toBe("warn");
		expect(out.bullets[0]).toMatch(/Checking/);
	});

	it("returns neutral with empty input", () => {
		expect(depositMixInsight([]).bullets).toHaveLength(0);
	});
});

describe("officerLoadInsight", () => {
	it("warns when a single officer holds >40%", () => {
		const out = officerLoadInsight([
			{ period: "Officer #01", balance: 50 },
			{ period: "Officer #02", balance: 30 },
			{ period: "Officer #03", balance: 20 },
		]);
		expect(out.tone).toBe("warn");
	});
});

describe("loanRateSpreadInsight", () => {
	it("warns when spread is under 2%", () => {
		const series = [
			{ period: "Jan", bar: 100, line: 2.5 },
			{ period: "Feb", bar: 100, line: 2.5 },
			{ period: "Mar", bar: 100, line: 2.5 },
			{ period: "Apr", bar: 100, line: 1.8 },
		];
		const out = loanRateSpreadInsight(series);
		expect(out.tone).toBe("warn");
	});
});

describe("watchlistTrendInsight", () => {
	it("warns when count is rising", () => {
		const out = watchlistTrendInsight([
			{ month: "Jan", count: 5 },
			{ month: "Feb", count: 8 },
		]);
		expect(out.tone).toBe("warn");
	});
});

describe("changeByProductInsight", () => {
	it("calls out top gainer and biggest drag", () => {
		const out = changeByProductInsight([
			{ label: "Checking", value: 3 },
			{ label: "CDs", value: -2 },
			{ label: "Savings", value: 0.5 },
		]);
		expect(out.bullets.join(" ")).toMatch(/Checking/);
		expect(out.bullets.join(" ")).toMatch(/CDs/);
	});
});
