import { DATA_ACCURACY_CASES } from "./data/dataAccuracyCases";
import { FRAUD_CASES } from "./data/fraudCases";
import type { DisputeCase } from "./types";

/** Cases pinned to the top of the queue for the guided demo, in walk order. */
const DEMO_ORDER = ["CBD-5101", "CBD-5102", "CBD-4822"];

/**
 * All CBD cases (data-accuracy + Fraud). The three demo cases are pinned to the
 * top in walk order; the rest follow, sorted by SLA urgency (soonest due first).
 */
const ALL_CASES = [...DATA_ACCURACY_CASES, ...FRAUD_CASES];
const byId = new Map(ALL_CASES.map((c) => [c.id, c]));

const demoCases = DEMO_ORDER.map((id) => byId.get(id)).filter(
	(c): c is DisputeCase => Boolean(c),
);
const restCases = ALL_CASES.filter((c) => !DEMO_ORDER.includes(c.id)).sort(
	(a, b) => a.slaDueDate.localeCompare(b.slaDueDate),
);

export const DISPUTE_CASES: DisputeCase[] = [...demoCases, ...restCases];

export function getCaseById(id: string): DisputeCase | undefined {
	return DISPUTE_CASES.find((c) => c.id === id);
}

export function getMemberByNumber(memberNumber: string) {
	return DISPUTE_CASES.find((c) => c.member.memberNumber === memberNumber)
		?.member;
}
