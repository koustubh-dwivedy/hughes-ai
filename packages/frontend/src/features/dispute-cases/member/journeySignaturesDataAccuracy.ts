import type { MemberSignature } from "./journeyTypes";

/**
 * Hand-authored journey events for ACDV data-accuracy case members. Fabricated
 * mockup data. Marcus Bell (CBD-5102) is the demo case: his on-time March
 * payment is on the timeline, which the agent cross-references to confirm the
 * furnished 60-days-past-due mark is a reporting error.
 */
export const DATA_ACCURACY_SIGNATURES: Record<string, MemberSignature> = {
	// Marcus Bell — CBD-5102 (auto loan ****3391, disputed 60-DPD via code 106).
	"100827": {
		joinDate: "2017-08-14",
		events: [
			{
				date: "2017-08-14",
				type: "membership",
				summary: "Joined the credit union; opened a share account.",
			},
			{
				date: "2022-02-10",
				type: "application",
				summary: "Auto loan originated through Origence LOS (****3391).",
			},
			{
				date: "2026-01-05",
				type: "payment",
				channel: "Auto-pay",
				summary: "Auto-loan payment of $412 posted — on time",
				amount: 412,
			},
			{
				date: "2026-02-04",
				type: "payment",
				channel: "Auto-pay",
				summary: "Auto-loan payment of $412 posted — on time",
				amount: 412,
			},
			{
				date: "2026-02-28",
				type: "letter",
				channel: "e-Statement",
				summary:
					"March auto-loan statement generated — statement balance $12,662.00; payment of $412.00 due 03/05/2026",
				amount: 12662,
				reference: {
					type: "document",
					label: "Loan statement",
					asset: { kind: "statement" },
					preview: "Statement balance $12,662.00 · $412.00 due 03/05/2026.",
				},
			},
			{
				date: "2026-03-03",
				type: "payment",
				channel: "Auto-pay",
				summary:
					"Auto-loan payment of $412 posted — cleared on time (2 days before the 03/05 due date); remaining balance $12,250.00",
				amount: 412,
				reference: {
					type: "document",
					label: "Bank statement",
					asset: { kind: "bank_statement" },
					preview: "Statement shows the $412 payment cleared 2026-03-03.",
				},
			},
			{
				date: "2026-04-15",
				type: "furnishing",
				summary:
					"Tradeline furnished to bureaus — erroneously reported 60 days past due (Mar 2026).",
			},
			{
				date: "2026-07-05",
				type: "dispute",
				summary:
					"ACDV 240705-11188 received — consumer disputes the late mark (code 106) with a bank statement.",
			},
		],
	},
};
