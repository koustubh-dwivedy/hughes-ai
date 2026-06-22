import type { MemberSignature } from "./journeyTypes";

/**
 * Hand-authored signature events for fraud-case members — the meaningful thread
 * (membership, the complaint ladder, fraud/security, the dispute). The generator
 * fills routine activity around these. Fabricated mockup data.
 */
export const FRAUD_SIGNATURES: Record<string, MemberSignature> = {
	// Aisha Bello — CBD-4822 (new-account fraud → CFPB complaint).
	"100558": {
		joinDate: "2019-04-16",
		events: [
			{
				date: "2019-04-16",
				type: "membership",
				summary: "Joined the credit union; opened a primary share account.",
			},
			{
				date: "2019-04-16",
				type: "kyc",
				summary: "CIP / identity verification completed at onboarding.",
			},
			{
				date: "2021-08-09",
				type: "application",
				summary: "Auto loan application approved and funded.",
			},
			{
				date: "2026-04-28",
				type: "kyc",
				summary:
					"Address change processed — later found to predate the fraudulent card.",
			},
			{
				date: "2026-05-02",
				type: "card",
				summary:
					"New credit card account opened (****8820) — later disputed as fraud.",
			},
			{
				date: "2026-06-09",
				type: "complaint",
				tier: "T1",
				channel: "Secure message",
				summary: "First report of an unrecognized card via online banking.",
			},
			{
				date: "2026-06-10",
				type: "call",
				channel: "Phone / IVR",
				summary:
					"Inbound call — IVR authentication FAILED from an unknown number.",
				reference: {
					type: "call_recording",
					label: "Call · 2026-06-10 09:14",
					locator: "ivr/rec/2026-06-10-0914",
					preview: "Caller could not pass KBA; ANI not on file.",
					asset: { kind: "call_transcript" },
				},
			},
			{
				date: "2026-06-11",
				type: "complaint",
				tier: "T2",
				channel: "Branch",
				summary:
					"Escalated to a fraud specialist after front-line could not resolve.",
			},
			{
				date: "2026-06-12",
				type: "complaint",
				tier: "T3",
				channel: "CFPB",
				summary:
					"CFPB complaint filed disputing the card she says she never opened.",
				reference: {
					type: "document",
					label: "CFPB case #26-558201",
					url: "https://www.consumerfinance.gov/complaint/",
					asset: { kind: "cfpb_complaint" },
				},
			},
			{
				date: "2026-06-12",
				type: "dispute",
				summary: "Identity-theft dispute case CBD-4822 opened.",
			},
		],
	},
	// Daniel Foster — CBD-4835 (account takeover, no ITR on file).
	"100620": {
		joinDate: "2017-02-03",
		events: [
			{
				date: "2017-02-03",
				type: "membership",
				summary: "Joined the credit union; opened share + checking.",
			},
			{
				date: "2026-04-21",
				type: "application",
				summary: "Auto loan originated (****2204) — later disputed.",
			},
			{
				date: "2026-06-15",
				type: "fraud",
				channel: "Online banking",
				summary: "Password reset + new device enrolled (possible takeover).",
			},
			{
				date: "2026-06-17",
				type: "dispute",
				channel: "ACDV",
				summary: "Account-takeover dispute CBD-4835 received via e-OSCAR.",
			},
		],
	},
	// Grace Kim — CBD-4818 (confirmed third-party, blocked & suppressed).
	"100410": {
		joinDate: "2015-11-20",
		events: [
			{
				date: "2015-11-20",
				type: "membership",
				summary: "Long-tenured member; joined with a share certificate.",
			},
			{
				date: "2026-03-30",
				type: "application",
				summary:
					"Personal loan opened (****9043) — later confirmed fraudulent.",
			},
			{
				date: "2026-06-05",
				type: "complaint",
				tier: "T2",
				channel: "Phone",
				summary: "Reported the loan as identity theft with an FTC affidavit.",
				reference: {
					type: "document",
					label: "FTC ITR #26-410773",
					url: "https://www.identitytheft.gov/",
					asset: { kind: "ftc_id_theft_report" },
				},
			},
			{
				date: "2026-06-08",
				type: "fraud",
				summary: "Card reissued; linked deposit account flagged.",
			},
			{
				date: "2026-06-10",
				type: "furnishing",
				summary:
					"Tradeline blocked (§605B) and suppressed from bureau furnishing.",
			},
			{
				date: "2026-06-11",
				type: "dispute",
				summary: "Dispute CBD-4818 resolved — confirmed third-party fraud.",
			},
		],
	},
};
