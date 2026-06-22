/**
 * Plain-language explainers for each validation source and deterministic gate,
 * shown in info-hovers so the reviewer knows what a check actually does.
 * Illustrative (demo mockup).
 */
export const SIGNAL_EXPLAINER: Record<string, string> = {
	"Core CIP (at opening)":
		"Compares the name, SSN, and DOB captured by the Customer Identification Program at account opening against the member system-of-record.",
	"Registered phone/email":
		"Compares the account's enrolled phone and email against the member's long-standing contact details on file.",
	"Pindrop (IVR)":
		"Voice biometric plus call-metadata (ANI, device, behavior) analysis across the member's call history.",
	"LexisNexis InstantID":
		"Verifies name, address, SSN, DOB, and phone against LexisNexis referential data covering nearly all US adults.",
	"LexisNexis FraudPoint":
		"Statistical model that scores fraud and material-misrepresentation risk, returning reason codes.",
	"LexisNexis Phone Finder":
		"Links a phone number to the identities associated with it across public and proprietary records, ranked by confidence.",
	Prove:
		"Confirms possession and ownership of the phone line and flags recent SIM-swap or porting events.",
	"Twilio Lookup":
		"Returns the carrier line type (mobile/VoIP/landline) and an identity-match result for a name and phone.",
	SentiLink:
		"Scores synthetic-identity and identity-theft risk from patterns in the applied PII.",
};

export const GATE_EXPLAINER: Record<string, string> = {
	"Identity Theft Report on file":
		"FCRA §605B requires a consumer Identity Theft Report (FTC affidavit, optionally a police report) before a furnisher blocks and suppresses an identity-theft tradeline.",
	"Within §605B 4-business-day block window":
		"Once a complete Identity Theft Report is received, the block/suppression must be actioned within four business days.",
	"Debt collection prohibition applies":
		"A debt resulting from identity theft may not be sold, transferred, or placed for collection.",
	"§605B block prerequisites met":
		"All conditions required to invoke the §605B block are satisfied.",
};

export function explainSignal(source: string): string | undefined {
	return SIGNAL_EXPLAINER[source];
}

export function explainGate(check: string): string | undefined {
	return GATE_EXPLAINER[check];
}
