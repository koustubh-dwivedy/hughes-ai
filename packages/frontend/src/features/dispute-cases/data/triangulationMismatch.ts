import type { TriangulationRow } from "../types";

/**
 * Triangulation for a confirmed third-party (impostor) case — drives a "block"
 * recommendation: 5 signals support fraud, 1 argues against, 3 inconclusive.
 * Each row carries the agent's per-signal resolution + the raw datapoints.
 * Fabricated mockup data.
 */
export const TRIANGULATION_MISMATCH: TriangulationRow[] = [
	{
		pillar: "Possession",
		source: "Prove",
		signal: "Possession · SIM-swap check",
		result: "Mismatch",
		stance: "supports",
		resolution:
			"Possession of the enrollment line could not be confirmed, and the carrier shows a SIM-swap 9 days before the account was opened — consistent with takeover of the number used to enroll.",
		dataPoints: [
			{ label: "Possession confirmed", value: "No", match: "mismatch" },
			{ label: "Trust score", value: "0.18 (low)", match: "mismatch" },
			{
				label: "SIM-swap",
				value: "2026-04-23 (9d pre-open)",
				match: "mismatch",
			},
			{ label: "Line tenure", value: "11 days", match: "mismatch" },
		],
		reference: {
			type: "api_record",
			label: "Prove trust score",
			url: "https://www.prove.com/",
		},
	},
	{
		pillar: "Internal",
		source: "Registered phone/email",
		signal: "Enrolled contacts vs member of record",
		result: "Mismatch",
		stance: "supports",
		resolution:
			"The enrollment phone differs from the member's number of record (5-year tenure), and the enrollment email is a free-mail address created two days before opening.",
		dataPoints: [
			{
				label: "Member phone (on file)",
				value: "(206) 555-0123",
				match: "neutral",
			},
			{ label: "Enrollment phone", value: "(206) 555-0190", match: "mismatch" },
			{ label: "Member email", value: "a.bello@example.com", match: "neutral" },
			{
				label: "Enrollment email",
				value: "free-mail, 2d old",
				match: "mismatch",
			},
		],
	},
	{
		pillar: "Referential",
		source: "LexisNexis Phone Finder",
		signal: "Phone ↔ identity linkage",
		result: "Mismatch",
		stance: "supports",
		resolution:
			"Phone Finder returned two identities linked to the enrollment number; neither carries the member's LexID. AI resolved this as no-link to the member (the member's LexID was absent from the ranked candidates).",
		dataPoints: [
			{ label: "Enrollment phone", value: "(206) 555-0190", match: "neutral" },
			{
				label: "Candidate 1",
				value: "J. Marsh · Tacoma WA · LexID≠member",
				match: "mismatch",
			},
			{ label: "Candidate 2", value: "thin / unscored", match: "neutral" },
			{ label: "Member LexID present?", value: "No", match: "mismatch" },
		],
		reference: {
			type: "api_record",
			label: "Phone Finder linkage",
			url: "https://risk.lexisnexis.com/products/instantid",
		},
	},
	{
		pillar: "Possession",
		source: "Twilio Lookup",
		signal: "Line type + identity match",
		result: "Elevated",
		stance: "supports",
		resolution:
			"The enrollment line resolves to a VoIP carrier, and Identity Match returned 'no match' for the member name paired with the enrollment phone.",
		dataPoints: [
			{ label: "Line type", value: "VoIP", match: "mismatch" },
			{ label: "Carrier", value: "Bandwidth.com", match: "neutral" },
			{ label: "Identity match", value: "No match", match: "mismatch" },
		],
		reference: {
			type: "api_record",
			label: "Twilio Lookup result",
			url: "https://www.twilio.com/docs/lookup",
		},
	},
	{
		pillar: "Possession",
		source: "SentiLink",
		signal: "ID-theft score",
		result: "Elevated",
		stance: "supports",
		resolution:
			"The identity-theft score is 0.71, above the 0.60 action threshold. Top contributors are PII recombination and a recent address change immediately before the application.",
		dataPoints: [
			{ label: "ID-theft score", value: "0.71", match: "mismatch" },
			{ label: "Threshold", value: "0.60", match: "neutral" },
			{ label: "Top reason", value: "PII recombination", match: "mismatch" },
			{
				label: "Second reason",
				value: "address change pre-app",
				match: "mismatch",
			},
		],
		reference: {
			type: "api_record",
			label: "SentiLink ID-theft score",
			url: "https://www.sentilink.com/",
		},
	},
	{
		pillar: "Internal",
		source: "Core CIP (at opening)",
		signal: "Name · SSN · DOB at opening",
		result: "Match",
		stance: "against",
		resolution:
			"The name, SSN, and DOB captured at opening match the member system-of-record exactly. A clean PII match is also what a first-party (member-opened) account looks like, so this weakly argues against third-party fraud.",
		dataPoints: [
			{ label: "Name", value: "Exact match", match: "match" },
			{ label: "SSN", value: "Exact match", match: "match" },
			{ label: "DOB", value: "Exact match", match: "match" },
			{ label: "Distinguishes impostor?", value: "No", match: "neutral" },
		],
	},
	{
		pillar: "Internal",
		source: "Pindrop (IVR)",
		signal: "Voice + ANI on prior calls",
		result: "Match",
		stance: "inconclusive",
		resolution:
			"The voiceprint matched the genuine member on calls from 2024–2025, but no call is tied to this account's enrollment or activity, so it cannot be time-bound to the disputed events.",
		dataPoints: [
			{
				label: "Voiceprint match",
				value: "Yes (2024–25 calls)",
				match: "match",
			},
			{ label: "Call tied to enrollment?", value: "None", match: "neutral" },
		],
		reference: {
			type: "call_recording",
			label: "Call · 2026-05-11 14:03",
			locator: "ivr/rec/2026-05-11-1403",
			asset: { kind: "call_transcript" },
		},
	},
	{
		pillar: "Referential",
		source: "LexisNexis InstantID",
		signal: "Identity element verification",
		result: "Match",
		stance: "inconclusive",
		resolution:
			"Name, address, SSN, DOB, and phone verify at index 50/50 — confirming the PII belongs to a real person, but this does not establish who actually controlled the account.",
		dataPoints: [
			{ label: "Verification index", value: "50 / 50", match: "match" },
			{
				label: "Elements verified",
				value: "name·addr·SSN·DOB·phone",
				match: "match",
			},
			{ label: "Distinguishes impostor?", value: "No", match: "neutral" },
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
		result: "Elevated",
		stance: "inconclusive",
		resolution:
			"FraudPoint is 612 with reason codes for address velocity and a thin file at the address. This is model-level risk, not specific to whether this member was impersonated.",
		dataPoints: [
			{ label: "Score", value: "612", match: "neutral" },
			{ label: "Reason", value: "address velocity", match: "neutral" },
			{ label: "Reason", value: "thin file at address", match: "neutral" },
		],
		reference: {
			type: "api_record",
			label: "FraudPoint score detail",
			url: "https://risk.lexisnexis.com/products/instantid",
		},
	},
];
