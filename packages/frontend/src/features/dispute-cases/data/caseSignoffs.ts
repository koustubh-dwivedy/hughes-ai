import type { Signoff } from "./caseProgressStore";

/**
 * Human sign-offs already recorded for the gates each case has cleared — keyed
 * by case id, then by stage index. Seeds the session store so a case sitting
 * past a gate (or resolved) shows the reviewer's recorded option + notes,
 * instead of a blank gate. Fabricated mockup data.
 *
 * Stage indices: Fraud (0 Intake, 1 Triangulate & decide). Only already-cleared
 * gates are seeded; the active gate is left blank for the human to complete.
 */
export const INITIAL_SIGNOFFS: Record<string, Record<number, Signoff>> = {
	// ---- Fraud --------------------------------------------------------------
	"CBD-4822": {
		0: {
			option: "confirm",
			comments:
				"ITR and police report cross-checked against the affidavit; member details consistent.",
		},
	},
	"CBD-4835": {
		0: {
			option: "flag",
			comments:
				"ACDV narrative only — no Identity Theft Report on file yet; flagged for follow-up before any block.",
		},
	},
	"CBD-4818": {
		// No intake AI panel for this case, so only the investigation gate applies.
		1: {
			option: "approve",
			comments:
				"Confirmed third-party: FTC affidavit + Everett PD report verified; possession and phone-linkage both failed while CIP matched. Approving §605B block.",
		},
	},
};

export function getInitialSignoffs(id: string): Record<number, Signoff> {
	return INITIAL_SIGNOFFS[id] ?? {};
}
