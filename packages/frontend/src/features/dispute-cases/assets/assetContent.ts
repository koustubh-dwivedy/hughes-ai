import type { AssetKind, EvidenceReference } from "../ai/aiTypes";
import { formatDate } from "../format";

export interface Address {
	name: string;
	lines: string[];
}

/** A business letter (sender/recipient blocks, body, signature). */
export interface LetterContent {
	format: "letter";
	kind: AssetKind;
	title: string;
	sender: Address;
	date: string;
	recipient: Address;
	re?: string;
	salutation: string;
	body: string[];
	closing: string;
	signatory: { name: string; title?: string };
	enclosures?: string[];
	/** Small straight margin note for received inbound mail. */
	receivedNote?: string;
	/** Light DRAFT header. */
	draft?: boolean;
}

/** A form/affidavit (header + labelled fields + body). */
export interface FormContent {
	format: "form";
	kind: AssetKind;
	title: string;
	header: string;
	subheader?: string;
	meta: { label: string; value: string }[];
	body: string[];
	signatory?: { name: string; title?: string };
	receivedNote?: string;
}

export interface TranscriptContent {
	format: "transcript";
	kind: AssetKind;
	title: string;
	header: string;
	meta: { label: string; value: string }[];
	lines: { speaker: string; text: string }[];
}

export type AssetContent = LetterContent | FormContent | TranscriptContent;

export interface AssetContext {
	memberName?: string;
	memberAddress?: string;
	date?: string;
	accountRef?: string;
}

const CU = "Cascade Federal Credit Union";
const CU_ADDR = ["1200 Riverside Avenue", "Spokane, WA 99201"];

export function buildAssetContent(
	kind: AssetKind,
	reference: EvidenceReference,
	ctx: AssetContext = {},
): AssetContent {
	const who = ctx.memberName ?? "The Member";
	const addr = ctx.memberAddress ?? "[address on file]";
	const on = ctx.date ? formatDate(ctx.date) : formatDate("2026-06-14");
	const acct = ctx.accountRef ?? "****0000";
	const title = reference.asset?.title ?? reference.label;

	switch (kind) {
		case "dispute_letter":
			return {
				format: "letter",
				kind,
				title,
				sender: { name: who, lines: [addr] },
				date: on,
				recipient: {
					name: CU,
					lines: ["Attn: Credit Reporting Disputes", ...CU_ADDR],
				},
				re: `Dispute of account ${acct} — Fair Credit Reporting Act`,
				salutation: "Dear Sir or Madam,",
				body: [
					`I am writing to formally dispute information ${CU} is reporting in my name. This is a written dispute under the Fair Credit Reporting Act, 15 U.S.C. §1681i and §1681s-2.`,
					"The tradeline does not comply with Metro 2 reporting standards. The Date of First Delinquency, account status, and balance do not agree across the credit bureaus, which makes the reporting inaccurate and unverifiable.",
					"I request that you conduct a reasonable investigation, provide verification of the exact Metro 2 fields you are furnishing, or delete the tradeline. Please respond to me in writing at the address above.",
				],
				closing: "Sincerely,",
				signatory: { name: who },
				enclosures: ["Copy of credit report excerpt"],
				receivedNote: `Received ${on}`,
			};
		case "ftc_id_theft_report":
			return {
				format: "form",
				kind,
				title,
				header: "Federal Trade Commission",
				subheader:
					"Identity Theft Report — Sworn Statement (IdentityTheft.gov)",
				meta: [
					{ label: "Report number", value: reference.label },
					{ label: "Affiant", value: who },
					{ label: "Date filed", value: on },
				],
				body: [
					`I, ${who}, declare under penalty of perjury that the account(s) identified in this report were opened or used without my knowledge, authorization, or consent as a result of identity theft.`,
					"I did not receive any benefit, money, goods, or services as a result of these account(s). I have filed a report with my local police department and authorize an investigation of this matter.",
					"I request, under FCRA §605B, that the furnisher block and cease reporting the fraudulent information and not place the debt for collection.",
				],
				signatory: { name: who, title: "Affiant" },
				receivedNote: `Received ${on}`,
			};
		case "acdv":
			return {
				format: "form",
				kind,
				title,
				header: "e-OSCAR",
				subheader: "Automated Consumer Dispute Verification (ACDV)",
				meta: [
					{ label: "Control number", value: reference.label },
					{ label: "Dispute code", value: "103 — Account opened fraudulently" },
					{ label: "Account", value: acct },
					{ label: "Consumer", value: who },
				],
				body: [
					"A consumer dispute was received by the credit reporting agency and routed to your institution for verification.",
					`Consumer statement: "${who} states this account resulted from account takeover and disputes the recent transactions."`,
					"Furnisher must investigate and respond with a corrected AUD or verification within the FCRA timeframe.",
				],
				receivedNote: `Received ${on}`,
			};
		case "cfpb_complaint":
			return {
				format: "form",
				kind,
				title,
				header: "Consumer Financial Protection Bureau",
				subheader: "Consumer Complaint — forwarded to company for response",
				meta: [
					{ label: "Complaint", value: reference.label },
					{ label: "Consumer", value: who },
					{ label: "Product", value: "Credit reporting" },
					{ label: "Date received", value: on },
				],
				body: [
					"Issue: Incorrect information on credit report — account the consumer states they never opened, or a disputed balance.",
					`What happened: ${who} states the disputed account does not belong to them or the balance is incorrect, and the furnisher continued reporting it.`,
					"Desired resolution: investigate, correct or delete the tradeline, and confirm to the consumer in writing.",
				],
				receivedNote: `Received ${on}`,
			};
		case "statement":
			return {
				format: "form",
				kind,
				title,
				header: CU,
				subheader: "Account Statement",
				meta: [
					{ label: "Member", value: who },
					{ label: "Account", value: acct },
					{ label: "Statement date", value: on },
				],
				body: [
					"Opening balance, deposits and credits, withdrawals and debits, fees assessed, and closing balance for the statement period are itemized in the enclosed detail.",
					"Please review your statement and report any discrepancy within 60 days.",
				],
			};
		case "call_transcript":
			return {
				format: "transcript",
				kind,
				title,
				header: `${CU} · Contact-center recording`,
				meta: [
					{ label: "Recording", value: reference.label },
					{ label: "Member", value: who },
				],
				lines: [
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
			// Outbound verification letter from the credit union.
			return {
				format: "letter",
				kind,
				title,
				sender: {
					name: CU,
					lines: ["Member Resolution Department", ...CU_ADDR],
				},
				date: on,
				recipient: { name: who, lines: [addr] },
				re: `Verification of debt — account ${acct}`,
				salutation: `Dear ${who},`,
				body: [
					"This communication is from a debt collector. This letter provides verification of the debt referenced in your dispute.",
					`The creditor of record is ${CU}. The account number is ${acct}. The itemized balance, including principal, interest, and fees since the date of first delinquency, is enclosed with supporting documentation.`,
					"If you have questions about this verification, please contact the Member Resolution Department at the number on your statement.",
				],
				closing: "Sincerely,",
				signatory: { name: "J. Mercer", title: "Member Resolution Specialist" },
				enclosures: [
					"Signed account agreement",
					"Account statements",
					"Payment history",
				],
			};
	}
}
