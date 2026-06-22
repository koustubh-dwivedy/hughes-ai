import type { CaseAi } from "../ai/aiTypes";

/** Fabricated AI artifacts for VOD cases (mockup) — intake SOR match + QA. */
export const AI_VOD: Record<string, CaseAi> = {
	"CBD-4821": {
		intake: {
			confidence: "high",
			sourceDoc: {
				type: "document",
				label: "Dispute letter (ACDV)",
				asset: { kind: "dispute_letter" },
				preview: "Inbound ACDV dispute matched to the member of record.",
			},
			fields: [
				{ label: "Dispute basis", value: "Debt not valid / amount disputed" },
			],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Jordan Rivera",
						sor: "Jordan Rivera",
						match: "match",
					},
					{
						field: "SSN",
						received: "***-**-4471",
						sor: "***-**-4471",
						match: "match",
					},
					{
						field: "DOB",
						received: "1986-03-22",
						sor: "1986-03-22",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****3391",
						sor: "****3391",
						match: "match",
					},
					{
						field: "Address",
						received: "418 Cedar St, Spokane WA",
						sor: "418 Cedar St, Spokane WA",
						match: "match",
					},
				],
			},
		},
		validationQa: {
			complete: true,
			discrepancies: [],
			recommendation: "validate",
			recommendationLabel: "Validate debt",
			confidence: "high",
		},
	},
	"CBD-4823": {
		intake: {
			confidence: "medium",
			sourceDoc: {
				type: "document",
				label: "Dispute letter (direct)",
				asset: { kind: "dispute_letter" },
				preview: "Direct written dispute — identity matched, address differs.",
			},
			fields: [{ label: "Dispute basis", value: "Debt not valid" }],
			sorMatch: {
				result: "partial",
				confidence: "medium",
				comparisons: [
					{
						field: "Name",
						received: "Maria Delgado",
						sor: "Maria Delgado",
						match: "match",
					},
					{
						field: "SSN",
						received: "***-**-2280",
						sor: "***-**-2280",
						match: "match",
					},
					{
						field: "DOB",
						received: "1979-11-05",
						sor: "1979-11-05",
						match: "match",
					},
					{
						field: "Loan #",
						received: "****7714",
						sor: "****7714",
						match: "match",
					},
					{
						field: "Address",
						received: "55 Pine St, Tacoma WA",
						sor: "92 Birch Ave, Tacoma WA",
						match: "partial",
					},
				],
			},
		},
		validationQa: {
			complete: true,
			discrepancies: [],
			recommendation: "validate",
			recommendationLabel: "Validate debt",
			confidence: "high",
		},
	},
	"CBD-4830": {
		intake: {
			confidence: "medium",
			sourceDoc: {
				type: "document",
				label: "CFPB complaint narrative",
				url: "https://www.consumerfinance.gov/complaint/",
				asset: { kind: "cfpb_complaint" },
				preview: "Member disputes the balance via a CFPB complaint.",
			},
			fields: [{ label: "Dispute basis", value: "Amount disputed" }],
			sorMatch: {
				result: "matched",
				confidence: "high",
				comparisons: [
					{
						field: "Name",
						received: "Thomas Nguyen",
						sor: "Thomas Nguyen",
						match: "match",
					},
					{
						field: "SSN",
						received: "***-**-9012",
						sor: "***-**-9012",
						match: "match",
					},
					{
						field: "DOB",
						received: "1991-07-30",
						sor: "1991-07-30",
						match: "match",
					},
					{
						field: "Card #",
						received: "****5560",
						sor: "****5560",
						match: "match",
					},
					{
						field: "Address",
						received: "1203 Alder Loop, Bellevue WA",
						sor: "1203 Alder Loop, Bellevue WA",
						match: "match",
					},
				],
			},
		},
		validationQa: {
			complete: false,
			discrepancies: [
				"Payment history not available from core for this account",
			],
			recommendation: "needs_more_info",
			recommendationLabel: "Retrieve payment history before validating",
			confidence: "medium",
		},
	},
};
