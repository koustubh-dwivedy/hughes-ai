import { FRAUD_CASES } from "./data/fraudCases";
import { VOD_CASES } from "./data/vodCases";
import type { DisputeCase } from "./types";

/** All CBD cases (VOD + Fraud), sorted by SLA urgency (soonest due first). */
export const DISPUTE_CASES: DisputeCase[] = [...VOD_CASES, ...FRAUD_CASES].sort(
	(a, b) => a.slaDueDate.localeCompare(b.slaDueDate),
);

export function getCaseById(id: string): DisputeCase | undefined {
	return DISPUTE_CASES.find((c) => c.id === id);
}

export function getMemberByNumber(memberNumber: string) {
	return DISPUTE_CASES.find((c) => c.member.memberNumber === memberNumber)
		?.member;
}
