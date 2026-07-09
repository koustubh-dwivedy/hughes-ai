import type { CaseAi } from "../ai/aiTypes";

/**
 * Fabricated AI artifacts for ACDV data-accuracy cases (mockup). Intake extracts
 * the disputed field + confirms the identity match; the investigation records the
 * three autonomy gates as deterministic checks plus the recommended response.
 * AI is evidence-gathering only — it never mutates case state.
 */
const acdvDoc = (control: string) =>
	({
		type: "document",
		label: control,
		asset: { kind: "acdv", title: `ACDV ${control}` },
		preview: "Inbound ACDV routed to the furnisher for investigation.",
	}) as const;

export const AI_DATA_ACCURACY: Record<string, CaseAi> = {
	"CBD-5101": {
		intake: {
			confidence: "high",
			sourceDoc: acdvDoc("240706-11204"),
			fields: [
				{ label: "Disputed field", value: "Current Balance" },
				{ label: "Reason code", value: "118 — Current balance / past due" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Dana Whitfield",
						sor: "Dana Whitfield",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****4471",
						sor: "****4471",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "modify",
			recommendationLabel: "Correct current balance → Response 21",
			confidence: "high",
			rationale:
				"Core shows $7,980 as of the Date of Account Information; the $8,400 furnished is stale (a $420 payment posted after the last furnish). Corrected value refurnished; delinquency status unchanged, so no derogatory flip.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "pass",
					basis: "0 attachments on the ACDV",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "pass",
					basis: "No free-text present",
				},
				{
					check: "Core field populated & Metro 2-consistent",
					status: "pass",
					basis: "Current Balance populated; no open+charge-off contradiction",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "core.getBalance(as_of=2026-06-30)" },
				{
					kind: "tool_result",
					label: "$7,980 (payment $420 posted 2026-06-28)",
				},
				{
					kind: "thinking",
					label:
						"Amount refresh only — not a status/derogatory change → autonomous",
				},
			],
		},
	},
	"CBD-5102": {
		intake: {
			confidence: "medium",
			sourceDoc: acdvDoc("240705-11188"),
			fields: [
				{ label: "Disputed field", value: "Account Status / Payment History" },
				{ label: "Reason code", value: "106 — Status / payment history" },
				{
					label: "⚠ Free-text",
					value: "Expands the code (balance + closed claims)",
				},
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Marcus Bell",
						sor: "Marcus Bell",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****3391",
						sor: "****3391",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "modify",
			recommendationLabel:
				"Correct payment rating + balance → Response 22 (approve)",
			confidence: "high",
			rationale:
				"The consumer attached a bank statement showing the March auto-loan payment cleared on time. The agent OCR'd the statement, extracted the $412 payment, and matched it to the member's transaction history — the payment posted 2026-03-03, two days before the 03/05 due date. The on-time payment is confirmed, so the furnished 60-days-past-due is a reporting error. The agent recommends correcting the payment rating to current and refreshing the balance. Because this flips a derogatory mark to positive and the ACDV carries a consumer image plus free-text, a human approves before it is furnished.",
			deterministicChecks: [
				{
					check: "Payment extracted from consumer image",
					status: "pass",
					basis: "consumer_statement.tiff → $412 auto-pay, cleared 2026-03-03",
				},
				{
					check: "Matched to member transaction history",
					status: "pass",
					basis:
						"Core shows $412 posted 2026-03-03 (on time) — see customer journey",
				},
				{
					check: "Human review required (consumer image + derogatory flip)",
					status: "fail",
					basis:
						"Image on file + status flips derog→positive → mandatory sign-off",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "ocr.extract(consumer_statement.tiff)" },
				{
					kind: "tool_result",
					label: "March auto-loan payment $412 — cleared 2026-03-03",
				},
				{ kind: "tool_call", label: "core.getTransactions(****3391)" },
				{
					kind: "tool_result",
					label:
						"$412 posted 2026-03-03 (2 days before 03/05 due) — matches statement",
				},
				{
					kind: "thinking",
					label:
						"On-time payment confirmed → furnished 60-DPD is wrong; recommend correct to current + balance. Image + derog flip → human approves.",
				},
			],
		},
	},
	"CBD-5103": {
		intake: {
			confidence: "high",
			sourceDoc: acdvDoc("240704-10902"),
			fields: [
				{ label: "Disputed field", value: "Date of First Delinquency" },
				{ label: "Reason code", value: "115 — DOFD" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Elena Cruz",
						sor: "Elena Cruz",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****7712",
						sor: "****7712",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "modify",
			recommendationLabel: "Correct DOFD → Response 21",
			confidence: "high",
			rationale:
				"Furnished DOFD 2026-03-01 was advanced past the original 2025-11-15 that led to the current status — re-aging. Corrected to the original DOFD; the 7-year clock is never advanced.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "pass",
					basis: "0 attachments",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "pass",
					basis: "No free-text present",
				},
				{
					check: "Anti-re-aging: DOFD not advanced",
					status: "pass",
					basis: "Corrected to earliest original DOFD 2025-11-15",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "core.getDelinquencyHistory(****7712)" },
				{ kind: "tool_result", label: "First 30-DPD → 2025-11-15" },
				{
					kind: "thinking",
					label: "Restore original DOFD; never advance → autonomous",
				},
			],
		},
	},
	"CBD-5104": {
		intake: {
			confidence: "low",
			sourceDoc: acdvDoc("240703-10777"),
			fields: [
				{ label: "Disputed field", value: "Unspecified (catch-all)" },
				{ label: "Reason code", value: "112 — Inaccurate information" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Priya Nair",
						sor: "Priya Nair",
						match: "match",
					},
					{
						field: "Card #",
						received: "****5560",
						sor: "****5560",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "verify",
			recommendationLabel: "Full-record verify → Response 24 (needs review)",
			confidence: "medium",
			rationale:
				"The consumer gave no specific field. A full-record check found status, balance, and dates all accurate, but a non-specific (112) dispute requires human confirmation before selecting Response 24.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "pass",
					basis: "0 attachments",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "fail",
					basis: "Free-text is non-specific — no field named",
				},
				{
					check: "Full-record fields verified",
					status: "pass",
					basis: "Status, balance, dates all match core",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "core.getFullTradeline(****5560)" },
				{ kind: "tool_result", label: "All furnished fields match core" },
				{
					kind: "thinking",
					label: "Non-specific → Response 24 only after human sign-off",
				},
			],
		},
	},
	"CBD-5105": {
		intake: {
			confidence: "medium",
			sourceDoc: acdvDoc("240702-10640"),
			fields: [
				{ label: "Disputed field", value: "Ownership (not his/hers)" },
				{ label: "Reason code", value: "001 — Not his/hers" },
			],
			sorMatch: {
				result: "matched",
				confidence: "medium",
				comparisons: [
					{
						field: "Name / SSN / DOB",
						received: "Robert Vance · ***-**-4402",
						sor: "Robert Vance · ***-**-4402",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****9901",
						sor: "****9901",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "verify",
			recommendationLabel: "Verify identity → Response 23 (needs review)",
			confidence: "low",
			rationale:
				"Identifiers match the member of record on a signed application, which leans verify — but the consumer attached a non-ownership affidavit. 'Not his/hers' is the most-litigated, most-abused template; any affidavit or image forces human review and a mixed-file check.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "fail",
					basis: "non_ownership_affidavit.tiff attached — must be viewed",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "pass",
					basis: "No free-text present",
				},
				{
					check: "Identity match on signed application",
					status: "pass",
					basis: "Name, SSN, DOB, loan # all match core",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "los.getSignedApplication(****9901)" },
				{
					kind: "tool_result",
					label: "Wet/e-signature on file matches member",
				},
				{
					kind: "thinking",
					label:
						"Affidavit contradicts a clean ID match — escalate mixed-file review",
				},
			],
		},
	},
	"CBD-5106": {
		intake: {
			confidence: "high",
			sourceDoc: acdvDoc("240707-11330"),
			fields: [
				{ label: "Disputed field", value: "Credit Limit" },
				{ label: "Reason code", value: "015 — Credit limit / original amount" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Sofia Marín",
						sor: "Sofia Marín",
						match: "match",
					},
					{
						field: "Card #",
						received: "****2048",
						sor: "****2048",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "modify",
			recommendationLabel: "Correct credit limit → Response 21",
			confidence: "high",
			rationale:
				"Core shows a $5,000 credit limit; the $3,000 furnished is stale from a prior limit increase. A limit correction is a factual field refresh with no derogatory impact.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "pass",
					basis: "0 attachments",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "pass",
					basis: "No free-text present",
				},
				{
					check: "Core field populated & Metro 2-consistent",
					status: "pass",
					basis: "Credit Limit populated at $5,000",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "core.getCreditLimit(****2048)" },
				{ kind: "tool_result", label: "$5,000 (increase posted 2024-08-01)" },
				{ kind: "thinking", label: "Limit refresh only → autonomous" },
			],
		},
	},
	"CBD-5107": {
		intake: {
			confidence: "high",
			sourceDoc: acdvDoc("240708-11412"),
			fields: [
				{ label: "Disputed field", value: "Date Opened" },
				{ label: "Reason code", value: "114 — Account dates" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Devin Park",
						sor: "Devin Park",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****6653",
						sor: "****6653",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "modify",
			recommendationLabel: "Correct date opened → Response 21",
			confidence: "high",
			rationale:
				"Origence LOS records the loan booked 2023-04-19; the furnished 2023-01-19 is a keying error. Date corrected to the system of record.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "pass",
					basis: "0 attachments",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "pass",
					basis: "No free-text present",
				},
				{
					check: "Core field populated & Metro 2-consistent",
					status: "pass",
					basis: "Date Opened populated in LOS",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "los.getBookingDate(****6653)" },
				{ kind: "tool_result", label: "Booked 2023-04-19" },
				{ kind: "thinking", label: "Date refresh only → autonomous" },
			],
		},
	},
	"CBD-5108": {
		intake: {
			confidence: "low",
			sourceDoc: acdvDoc("240701-10588"),
			fields: [
				{ label: "Disputed field", value: "Original Charge-off Amount" },
				{ label: "Reason code", value: "119 — Charge-off / payment amount" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Hannah Weiss",
						sor: "Hannah Weiss",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****4417",
						sor: "****4417",
						match: "match",
					},
				],
			},
		},
		investigation: {
			recommendation: "modify",
			recommendationLabel:
				"Correct charge-off amount → Response 22 (needs review)",
			confidence: "low",
			rationale:
				"The consumer disputes the charge-off amount, but the Original Charge-off Amount field is not populated in core — the value can't be substantiated internally. A blank/inconsistent field trips the third gate, so the correction is drafted for a human rather than auto-applied.",
			deterministicChecks: [
				{
					check: "No consumer image attached",
					status: "pass",
					basis: "0 attachments",
				},
				{
					check: "Free-text consistent with dispute code",
					status: "pass",
					basis: "No free-text present",
				},
				{
					check: "Core field populated & Metro 2-consistent",
					status: "fail",
					basis: "Original Charge-off Amount not populated in core",
				},
			],
			reasoning: [
				{ kind: "tool_call", label: "core.getChargeOffAmount(****4417)" },
				{ kind: "tool_result", label: "null — field not set at charge-off" },
				{
					kind: "thinking",
					label: "Cannot substantiate internally → draft for human",
				},
			],
		},
	},
};
