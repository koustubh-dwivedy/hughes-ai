import type { Signoff } from "./caseProgressStore";

/**
 * Human sign-offs already recorded for the gates each case has cleared — keyed
 * by case id, then by stage index. Seeds the session store so a case sitting
 * past a gate (or resolved) shows the reviewer's recorded option + notes,
 * instead of a blank gate. Fabricated mockup data.
 *
 * Stage indices: Fraud (0 Intake, 1 Triangulate & decide); VOD (0 Intake,
 * 5 Close). Only already-cleared gates are seeded; the active gate is left
 * blank for the human to complete.
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
	// ---- VOD ----------------------------------------------------------------
	"CBD-4821": {
		0: {
			option: "confirm",
			comments:
				"Identity matched to the member of record on all elements; proceeding with verification.",
		},
	},
	"CBD-4823": {
		0: {
			option: "confirm",
			comments: "Identity matched (address variance noted, within tolerance).",
		},
		5: {
			option: "approve",
			comments:
				"Verification package complete — signed agreement, statements, and payment history substantiate the debt. Validated.",
		},
	},
	"CBD-4830": {
		0: {
			option: "confirm",
			comments: "SOR identity match confirmed on name, SSN, DOB, and account.",
		},
	},
};

export function getInitialSignoffs(id: string): Record<number, Signoff> {
	return INITIAL_SIGNOFFS[id] ?? {};
}
