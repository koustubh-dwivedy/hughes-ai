import type { TriangulationRow } from "../types";

/**
 * Triangulation where identity is fully corroborated to the genuine member —
 * argues against third-party fraud. With no Identity Theft Report on file, the
 * recommendation is "needs more info" rather than a block. Fabricated mockup.
 */
export const TRIANGULATION_FIRST_PARTY: TriangulationRow[] = [
	{
		pillar: "Internal",
		source: "Core CIP (at opening)",
		signal: "Name · SSN · DOB at opening",
		result: "Match",
		stance: "against",
		resolution:
			"Identity captured at opening matches the member system-of-record exactly.",
		dataPoints: [
			{ label: "Name", value: "Exact match", match: "match" },
			{ label: "SSN", value: "Exact match", match: "match" },
			{ label: "DOB", value: "Exact match", match: "match" },
		],
	},
	{
		pillar: "Internal",
		source: "Registered phone/email",
		signal: "Enrolled contacts vs member of record",
		result: "Match",
		stance: "against",
		resolution:
			"The account's enrolled phone and email match the member's long-standing contacts of record.",
		dataPoints: [
			{ label: "Phone", value: "Matches on-file", match: "match" },
			{ label: "Email", value: "Matches on-file", match: "match" },
		],
	},
	{
		pillar: "Internal",
		source: "Pindrop (IVR)",
		signal: "Voice + ANI on prior calls",
		result: "Match",
		stance: "against",
		resolution:
			"Voiceprint matched the member on a recent call placed from the registered number.",
		dataPoints: [
			{ label: "Voiceprint match", value: "Yes (recent)", match: "match" },
			{ label: "ANI on file", value: "Yes", match: "match" },
		],
	},
	{
		pillar: "Referential",
		source: "LexisNexis InstantID",
		signal: "Identity element verification",
		result: "Match",
		stance: "against",
		resolution:
			"All identity elements verify and resolve to the member's LexID.",
		dataPoints: [
			{ label: "Verification index", value: "50 / 50", match: "match" },
			{ label: "Resolves to member LexID?", value: "Yes", match: "match" },
		],
		reference: {
			type: "api_record",
			label: "LexisNexis InstantID report",
			url: "https://risk.lexisnexis.com/products/instantid",
		},
	},
	{
		pillar: "Referential",
		source: "LexisNexis FraudPoint",
		signal: "Fraud-risk score",
		result: "Match",
		stance: "against",
		resolution: "FraudPoint is 188 (low risk) with no adverse reason codes.",
		dataPoints: [
			{ label: "Score", value: "188 (low)", match: "match" },
			{ label: "Reason codes", value: "None adverse", match: "match" },
		],
	},
	{
		pillar: "Possession",
		source: "Prove",
		signal: "Possession · ownership",
		result: "Match",
		stance: "against",
		resolution:
			"Possession and ownership of the registered line are confirmed; no SIM-swap history.",
		dataPoints: [
			{ label: "Possession confirmed", value: "Yes", match: "match" },
			{ label: "SIM-swap", value: "None", match: "match" },
		],
	},
	{
		pillar: "Possession",
		source: "Twilio Lookup",
		signal: "Line type + identity match",
		result: "Match",
		stance: "against",
		resolution:
			"Line type is mobile and Identity Match confirms the member as owner.",
		dataPoints: [
			{ label: "Line type", value: "Mobile", match: "match" },
			{ label: "Identity match", value: "Match", match: "match" },
		],
	},
	{
		pillar: "Internal",
		source: "Core CIP (at opening)",
		signal: "Identity Theft Report",
		result: "Mismatch",
		stance: "inconclusive",
		resolution:
			"No Identity Theft Report has been provided. Without an ITR the §605B block cannot be invoked, and the takeover claim cannot be confirmed — request the ITR before deciding.",
		dataPoints: [
			{ label: "ITR on file", value: "No", match: "mismatch" },
			{ label: "Police report", value: "Not provided", match: "mismatch" },
		],
	},
];
