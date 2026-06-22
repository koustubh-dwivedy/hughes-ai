import type { AssetKind, EvidenceReference } from "../ai/aiTypes";
import { formatDate } from "../format";

export interface AssetContent {
	kind: AssetKind;
	title: string;
	/** Document chrome label, e.g. "Cascade FCU · Member correspondence". */
	letterhead: string;
	meta: { label: string; value: string }[];
	paragraphs: string[];
	transcript?: { speaker: string; text: string }[];
}

export interface AssetContext {
	memberName?: string;
	date?: string;
}

const CU = "Cascade Federal Credit Union";

/**
 * Builds a plausible faux document for a mocked file asset. Pure — no I/O.
 * The content is illustrative only (demo mockup), not a real legal document.
 */
export function buildAssetContent(
	kind: AssetKind,
	reference: EvidenceReference,
	ctx: AssetContext = {},
): AssetContent {
	const who = ctx.memberName ?? "the member";
	const on = ctx.date ? formatDate(ctx.date) : "—";
	const title = reference.asset?.title ?? reference.label;

	switch (kind) {
		case "dispute_letter":
			return {
				kind,
				title,
				letterhead: "Inbound consumer dispute — received",
				meta: [
					{ label: "From", value: who },
					{ label: "Received", value: on },
					{ label: "Channel", value: reference.label },
				],
				paragraphs: [
					`To whom it may concern: I am disputing the following account reported by ${CU}. This is a formal dispute under the Fair Credit Reporting Act §611 and §623.`,
					"The tradeline does not comply with Metro 2 reporting standards. The Date of First Delinquency, account status, and balance fields are inconsistent across bureaus, rendering the reporting inaccurate and unverifiable.",
					"Per FCRA, you must conduct a reasonable investigation and provide verification of the exact Metro 2 fields, or delete the tradeline. Please treat this as my written dispute.",
				],
			};
		case "cfpb_complaint":
			return {
				kind,
				title,
				letterhead: "Consumer Financial Protection Bureau — Complaint",
				meta: [
					{ label: "Complaint", value: reference.label },
					{ label: "Consumer", value: who },
					{ label: "Submitted", value: on },
					{ label: "Product", value: "Credit reporting" },
				],
				paragraphs: [
					"Issue: Incorrect information on your report — account I never opened / amount disputed.",
					`What happened: ${who} states the disputed account does not belong to them or the balance is incorrect, and the credit union continued furnishing it.`,
					"Desired resolution: Investigate, correct or delete the tradeline, and confirm in writing.",
				],
			};
		case "ftc_id_theft_report":
			return {
				kind,
				title,
				letterhead: "FTC Identity Theft Report — IdentityTheft.gov",
				meta: [
					{ label: "Report", value: reference.label },
					{ label: "Affiant", value: who },
					{ label: "Filed", value: on },
				],
				paragraphs: [
					`I, ${who}, declare under penalty of perjury that the account(s) identified below were opened or used without my authorization as a result of identity theft.`,
					"A police report has been filed to support this affidavit (report number on file). I request that the furnisher block and cease reporting the fraudulent tradeline under FCRA §605B.",
					"I did not benefit from the account and authorize the investigation of this matter.",
				],
			};
		case "call_transcript":
			return {
				kind,
				title,
				letterhead: `${CU} · Contact-center recording`,
				meta: [
					{ label: "Recording", value: reference.label },
					{ label: "Member", value: who },
				],
				paragraphs: ["Auto-generated transcript (mock)."],
				transcript: [
					{
						speaker: "IVR",
						text: "Thanks for calling. Please say or enter your account number.",
					},
					{
						speaker: "Caller",
						text: "I'm calling about a charge I don't recognize.",
					},
					{
						speaker: "IVR",
						text: "I could not verify your identity from this number.",
					},
					{
						speaker: "Agent",
						text: "I see the call came from a number not on file — I'll need to step up verification.",
					},
				],
			};
		default:
			return {
				kind,
				title,
				letterhead: `${CU} · Member correspondence`,
				meta: [
					{ label: "Document", value: reference.label },
					{ label: "Member", value: who },
					{ label: "Date", value: on },
				],
				paragraphs: [
					`Dear ${who},`,
					kind === "statement"
						? "Enclosed is your account statement for the period. Balances, payments, and fees are itemized for your records."
						: "This letter provides verification of the debt referenced in your dispute, including the creditor, account number, itemization date, and current amount, with supporting documentation enclosed.",
					`Sincerely, ${CU} — Member Resolution`,
				],
			};
	}
}
