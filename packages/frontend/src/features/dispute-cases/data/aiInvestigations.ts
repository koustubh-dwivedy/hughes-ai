import type { CaseAi } from "../ai/aiTypes";
import { AI_FRAUD } from "./aiFraudCases";
import { AI_VOD } from "./aiVodCases";

/**
 * Per-case AI artifacts (mockup). Split into fraud/VOD files to stay under the
 * 300-line structural cap. AI is evidence-gathering only — never mutates state.
 */
export const CASE_AI: Record<string, CaseAi> = { ...AI_FRAUD, ...AI_VOD };

export function getCaseAi(id: string): CaseAi | undefined {
	return CASE_AI[id];
}
