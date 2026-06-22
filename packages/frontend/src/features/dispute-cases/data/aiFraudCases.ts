import type { CaseAi } from "../ai/aiTypes";

/** Fabricated AI artifacts for fraud cases (mockup). */
export const AI_FRAUD: Record<string, CaseAi> = {
	"CBD-4822": {
		intake: {
			confidence: "high",
			sourceDoc: {
				type: "document",
				label: "FTC Identity Theft Report (affidavit.pdf)",
				url: "https://www.identitytheft.gov/",
				preview: "Sworn FTC affidavit + Seattle PD report attached at intake.",
			},
			fields: [
				{ label: "Report type", value: "FTC Identity Theft Report" },
				{ label: "Reference #", value: "FTC-2026-558201" },
				{ label: "Police report", value: "Seattle PD #26-44821" },
				{ label: "Fraud sub-type", value: "New-account fraud" },
				{ label: "Disputed element", value: "Account ownership" },
			],
		},
		investigation: {
			recommendation: "block_605b",
			recommendationLabel: "Block tradeline (§605B)",
			confidence: "high",
			rationale:
				"Registered phone and Prove possession both mismatch the claimant, and Phone Finder resolves the claimant's number to a different identity. CIP captured at account opening matches the genuine member, and FraudPoint is elevated on address velocity — a pattern consistent with third-party new-account fraud rather than a first-party claim.",
			deterministicChecks: [
				{
					check: "Identity Theft Report on file",
					status: "pass",
					basis: "FTC affidavit + police report attached",
				},
				{
					check: "Within §605B 4-business-day block window",
					status: "pass",
					basis: "2 business days remaining",
				},
				{
					check: "Debt collection prohibition applies",
					status: "pass",
					basis: "ID-theft debt may not be placed for collection",
				},
			],
			reasoning: [
				{
					kind: "thinking",
					label: "Frame the question",
					detail:
						"Distinguish third-party identity theft from a first-party claim.",
				},
				{
					kind: "tool_call",
					label: "Pull CIP captured at account opening (core)",
				},
				{
					kind: "tool_result",
					label: "CIP matches the genuine member",
					detail: "Name · SSN · DOB consistent with the on-file member.",
				},
				{
					kind: "tool_call",
					label: "Query LexisNexis InstantID + FraudPoint + Phone Finder",
				},
				{
					kind: "tool_result",
					label: "FraudPoint elevated; Phone Finder mismatch",
					detail: "Claimant phone links to a different identity.",
				},
				{
					kind: "tool_call",
					label: "Check phone possession (Prove) + line type (Twilio)",
				},
				{
					kind: "tool_result",
					label: "Possession not confirmed; VoIP line, SIM-swap flag",
				},
				{
					kind: "thinking",
					label: "Synthesize",
					detail:
						"Possession + referential mismatches outweigh the CIP match → third-party.",
				},
			],
		},
	},
	"CBD-4835": {
		intake: {
			confidence: "medium",
			sourceDoc: {
				type: "api_record",
				label: "ACDV narrative (e-OSCAR)",
				preview:
					"Indirect dispute via ACDV; no Identity Theft Report attached.",
			},
			fields: [
				{ label: "Report type", value: "None on file" },
				{ label: "Fraud sub-type", value: "Account takeover" },
				{ label: "Disputed element", value: "Recent transactions" },
			],
		},
		investigation: {
			recommendation: "needs_more_info",
			recommendationLabel: "Request Identity Theft Report",
			confidence: "medium",
			rationale:
				"All identity signals match the genuine member — CIP, registered phone/email, voice + ANI, InstantID, FraudPoint low, and Prove possession confirmed. With no Identity Theft Report on file and identity fully corroborated, this looks closer to first-party; obtain an ITR (or withdrawal) before deciding.",
			deterministicChecks: [
				{
					check: "Identity Theft Report on file",
					status: "fail",
					basis: "No FTC affidavit / police report attached",
				},
				{
					check: "§605B block prerequisites met",
					status: "n_a",
					basis: "Block requires an Identity Theft Report",
				},
			],
			reasoning: [
				{
					kind: "tool_call",
					label: "Corroborate identity across internal + vendors",
				},
				{
					kind: "tool_result",
					label: "All sources match the genuine member",
					detail: "Possession confirmed; FraudPoint low.",
				},
				{
					kind: "thinking",
					label:
						"No ITR + full identity match → cannot confirm third-party fraud",
				},
			],
		},
	},
	"CBD-4818": {
		investigation: {
			recommendation: "block_605b",
			recommendationLabel: "Block tradeline (§605B)",
			confidence: "high",
			rationale:
				"Identity Theft Report on file and multiple possession/referential mismatches confirmed third-party identity theft. Block applied, re-furnishing prevented, and collection prohibited.",
			deterministicChecks: [
				{
					check: "Identity Theft Report on file",
					status: "pass",
					basis: "FTC affidavit + Everett PD report",
				},
				{
					check: "Block applied within window",
					status: "pass",
					basis: "Blocked on receipt",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "Triangulate identity across sources" },
				{
					kind: "tool_result",
					label: "Possession + Phone Finder mismatch; CIP match",
				},
				{
					kind: "thinking",
					label: "Confirmed third-party → block under §605B",
				},
			],
		},
	},
};
