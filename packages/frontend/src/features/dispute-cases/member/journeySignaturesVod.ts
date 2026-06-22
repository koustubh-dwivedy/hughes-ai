import type { MemberSignature } from "./journeyTypes";

/**
 * Hand-authored signature events for VOD-case members. The generator fills
 * routine activity around these. Fabricated mockup data.
 */
export const VOD_SIGNATURES: Record<string, MemberSignature> = {
	// Jordan Rivera — CBD-4821 (charged-off auto loan, VOD via ACDV).
	"100482": {
		joinDate: "2018-06-11",
		events: [
			{
				date: "2018-06-11",
				type: "membership",
				summary: "Joined the credit union; opened a share account.",
			},
			{
				date: "2022-09-02",
				type: "application",
				summary: "Auto loan originated through Origence LOS (****3391).",
			},
			{
				date: "2025-12-01",
				type: "delinquency",
				summary: "First missed payment (date of first delinquency).",
			},
			{
				date: "2026-02-15",
				type: "delinquency",
				summary: "Loan reaches 60 days past due; collections outreach begins.",
			},
			{
				date: "2026-04-02",
				type: "call",
				channel: "Phone",
				summary: "Collections call — member acknowledged the balance.",
				reference: {
					type: "call_recording",
					label: "Call · 2026-04-02 16:40",
					locator: "ivr/rec/2026-04-02-1640",
					asset: { kind: "call_transcript" },
				},
			},
			{
				date: "2026-03-31",
				type: "delinquency",
				summary: "Auto loan charged off after 120 days delinquent.",
			},
			{
				date: "2026-06-14",
				type: "dispute",
				channel: "ACDV",
				summary: "Validation-of-debt dispute CBD-4821 received via e-OSCAR.",
			},
		],
	},
	// Maria Delgado — CBD-4823 (VOD, validated, resolved).
	"100731": {
		joinDate: "2016-09-27",
		events: [
			{
				date: "2016-09-27",
				type: "membership",
				summary: "Joined the credit union with direct deposit.",
			},
			{
				date: "2024-01-18",
				type: "application",
				summary: "Personal loan originated (****7714).",
			},
			{
				date: "2026-02-01",
				type: "delinquency",
				summary: "Loan becomes delinquent (date of first delinquency).",
			},
			{
				date: "2026-06-01",
				type: "dispute",
				channel: "Direct",
				summary: "Direct VOD dispute CBD-4823 received in writing.",
				reference: {
					type: "document",
					label: "Dispute letter",
					asset: { kind: "dispute_letter" },
				},
			},
			{
				date: "2026-06-09",
				type: "letter",
				channel: "Certified mail",
				summary: "Debt verification package mailed to the member.",
				reference: {
					type: "document",
					label: "Verification letter",
					asset: { kind: "letter" },
				},
			},
		],
	},
	// Thomas Nguyen — CBD-4830 (VOD via CFPB, amount disputed).
	"100904": {
		joinDate: "2020-03-05",
		events: [
			{
				date: "2020-03-05",
				type: "membership",
				summary: "Joined the credit union; opened checking + credit card.",
			},
			{
				date: "2023-05-11",
				type: "card",
				summary: "Credit card account opened (****5560).",
			},
			{
				date: "2026-03-15",
				type: "delinquency",
				summary: "Card becomes delinquent (date of first delinquency).",
			},
			{
				date: "2026-06-18",
				type: "complaint",
				tier: "T3",
				channel: "CFPB",
				summary: "CFPB complaint disputing the card balance.",
				reference: {
					type: "document",
					label: "CFPB complaint narrative",
					url: "https://www.consumerfinance.gov/complaint/",
					asset: { kind: "cfpb_complaint" },
				},
			},
			{
				date: "2026-06-18",
				type: "dispute",
				summary: "Validation-of-debt dispute CBD-4830 opened.",
			},
		],
	},
};
