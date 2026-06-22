import type { AssetKind, EvidenceReference } from "../ai/aiTypes";
import { formatDate } from "../format";

export type StampTone = "red" | "blue" | "ink";

export interface Stamp {
	text: string;
	tone: StampTone;
}

export interface AssetContent {
	kind: AssetKind;
	/** "scanned" = printed-paper render; "transcript" = call-log render. */
	format: "scanned" | "transcript";
	title: string;
	/** Top-of-page letterhead organisation. */
	letterhead: string;
	/** Smaller descriptor under the letterhead. */
	subhead?: string;
	/** Inbound = received mail (sender's letterhead + RECEIVED stamp);
	 *  outbound = our letter (CU letterhead + signature). */
	direction: "inbound" | "outbound";
	meta: { label: string; value: string }[];
	paragraphs: string[];
	/** Hand signature block (printed name + optional title). */
	signature?: { name: string; title?: string };
	/** Rotated ink stamps overlaid on the page. */
	stamps?: Stamp[];
	transcript?: { speaker: string; text: string }[];
}

export interface AssetContext {
	memberName?: string;
	date?: string;
}

const CU = "Cascade Federal Credit Union";

/**
 * Builds a plausible faux document for a mocked file asset. Pure — no I/O.
 * Illustrative only (demo mockup), not a real legal document. Most kinds render
 * as a scanned printed page; call recordings render as a transcript.
 */
export function buildAssetContent(
	kind: AssetKind,
	reference: EvidenceReference,
	ctx: AssetContext = {},
): AssetContent {
	const who = ctx.memberName ?? "the member";
	const on = ctx.date ? formatDate(ctx.date) : "—";
	const received: Stamp = { text: `RECEIVED ${on}`, tone: "red" };
	const title = reference.asset?.title ?? reference.label;
	const base = { kind, title } as const;

	switch (kind) {
		case "dispute_letter":
			return {
				...base,
				format: "scanned",
				direction: "inbound",
				letterhead: who,
				subhead: "Consumer dispute correspondence",
				meta: [
					{ label: "To", value: `${CU} — Credit Disputes` },
					{ label: "Re", value: reference.label },
				],
				paragraphs: [
					`To whom it may concern: I am formally disputing the account ${CU} is reporting in my name. This is a written dispute under the Fair Credit Reporting Act §611 and §623.`,
					"The tradeline does not comply with Metro 2 reporting standards — the Date of First Delinquency, account status, and balance fields are inconsistent across the bureaus, making the reporting inaccurate and unverifiable.",
					"You must conduct a reasonable investigation and provide verification of the exact Metro 2 fields, or delete the tradeline. Please treat this as my written dispute and respond in writing.",
				],
				signature: { name: who },
				stamps: [received],
			};
		case "cfpb_complaint":
			return {
				...base,
				format: "scanned",
				direction: "inbound",
				letterhead: "Consumer Financial Protection Bureau",
				subhead: "Consumer Complaint — forwarded to company",
				meta: [
					{ label: "Complaint", value: reference.label },
					{ label: "Consumer", value: who },
					{ label: "Product", value: "Credit reporting" },
				],
				paragraphs: [
					"Issue: Incorrect information on your report — account I never opened / amount disputed.",
					`What happened: ${who} states the disputed account does not belong to them or the balance is incorrect, and the credit union continued furnishing it.`,
					"Desired resolution: investigate, correct or delete the tradeline, and confirm in writing. Submitted electronically via consumerfinance.gov.",
				],
				stamps: [received, { text: "CFPB", tone: "blue" }],
			};
		case "ftc_id_theft_report":
			return {
				...base,
				format: "scanned",
				direction: "inbound",
				letterhead: "Federal Trade Commission",
				subhead: "Identity Theft Report — sworn affidavit",
				meta: [
					{ label: "Report", value: reference.label },
					{ label: "Affiant", value: who },
				],
				paragraphs: [
					`I, ${who}, declare under penalty of perjury that the account(s) identified below were opened or used without my authorization as a result of identity theft.`,
					"A police report has been filed to support this affidavit (report number on file). I request that the furnisher block and cease reporting the fraudulent tradeline under FCRA §605B.",
					"I did not benefit from the account and I authorize the investigation of this matter.",
				],
				signature: { name: who, title: "Affiant" },
				stamps: [{ text: "SWORN", tone: "blue" }, received],
			};
		case "call_transcript":
			return {
				...base,
				format: "transcript",
				direction: "inbound",
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
		case "statement":
			return {
				...base,
				format: "scanned",
				direction: "outbound",
				letterhead: CU,
				subhead: "Account Statement",
				meta: [
					{ label: "Member", value: who },
					{ label: "Statement date", value: on },
				],
				paragraphs: [
					`Account summary for ${who}. Balances, payments, and fees for the statement period are itemized below for your records.`,
					"Opening balance, deposits and credits, withdrawals and debits, fees assessed, and closing balance are reflected in the enclosed detail.",
				],
				stamps: [{ text: "STATEMENT", tone: "ink" }],
			};
		default:
			return {
				...base,
				format: "scanned",
				direction: "outbound",
				letterhead: CU,
				subhead: "Member Resolution — debt verification",
				meta: [
					{ label: "To", value: who },
					{ label: "Date", value: on },
				],
				paragraphs: [
					`Dear ${who},`,
					"This letter provides verification of the debt referenced in your dispute, including the creditor, account number, itemization date, and current amount, with supporting documentation enclosed.",
					"If you have questions about this verification, please contact Member Resolution at the number on file.",
				],
				signature: { name: "J. Mercer", title: "Member Resolution Specialist" },
				stamps: [{ text: "MAILED · CERTIFIED", tone: "ink" }],
			};
	}
}
