import { describe, expect, it } from "vitest";
import { TAG_TYPES } from "./tags";

describe("TAG_TYPES", () => {
	it("declares the seven cache tags used across slices", () => {
		expect(TAG_TYPES).toEqual([
			"DepositPortfolio",
			"PastDue",
			"OfficerBranch",
			"ExecutiveSummary",
			"Trust",
			"History",
			"Ask",
		]);
	});

	it("contains no duplicates", () => {
		const set = new Set(TAG_TYPES);
		expect(set.size).toBe(TAG_TYPES.length);
	});
});
