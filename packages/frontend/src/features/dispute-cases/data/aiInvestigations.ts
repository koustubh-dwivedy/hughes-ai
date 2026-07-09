import type { CaseAi } from "../ai/aiTypes";
import { AI_DATA_ACCURACY } from "./aiDataAccuracyCases";
import { AI_FRAUD } from "./aiFraudCases";

/**
 * Per-case AI artifacts (mockup). Split into fraud/data-accuracy files to stay
 * under the 300-line structural cap. AI is evidence-gathering only — never
 * mutates state.
 */
export const CASE_AI: Record<string, CaseAi> = {
	...AI_FRAUD,
	...AI_DATA_ACCURACY,
};

export function getCaseAi(id: string): CaseAi | undefined {
	return CASE_AI[id];
}
