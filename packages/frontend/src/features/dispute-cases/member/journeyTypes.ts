import type { EvidenceReference } from "../ai/aiTypes";

/** Every kind of touchpoint a member can have with the credit union. */
export type TouchpointType =
	| "complaint"
	| "letter"
	| "call"
	| "message"
	| "email"
	| "branch"
	| "transaction"
	| "card"
	| "fee"
	| "payment"
	| "membership"
	| "kyc"
	| "application"
	| "delinquency"
	| "furnishing"
	| "dispute"
	| "fraud";

/** The four filterable families touchpoint types roll up into. */
export type TouchpointCategory =
	| "complaint"
	| "contact"
	| "money"
	| "lifecycle";

export type ComplaintTier = "T1" | "T2" | "T3";

export interface Touchpoint {
	/** ISO date (YYYY-MM-DD). */
	date: string;
	type: TouchpointType;
	/** Escalation tier (complaints only). */
	tier?: ComplaintTier;
	channel?: string;
	summary: string;
	/** Dollar amount for money-movement touchpoints. */
	amount?: number;
	reference?: EvidenceReference;
}

/** The hand-authored backbone of a member's journey (the meaningful thread). */
export interface MemberSignature {
	joinDate: string;
	events: Touchpoint[];
}

export const TYPE_CATEGORY: Record<TouchpointType, TouchpointCategory> = {
	complaint: "complaint",
	letter: "complaint",
	call: "contact",
	message: "contact",
	email: "contact",
	branch: "contact",
	transaction: "money",
	card: "money",
	fee: "money",
	payment: "money",
	membership: "lifecycle",
	kyc: "lifecycle",
	application: "lifecycle",
	delinquency: "lifecycle",
	furnishing: "lifecycle",
	dispute: "lifecycle",
	fraud: "lifecycle",
};

export const CATEGORY_LABEL: Record<TouchpointCategory, string> = {
	complaint: "Complaints",
	contact: "Contacts",
	money: "Money",
	lifecycle: "Lifecycle",
};

export const TYPE_LABEL: Record<TouchpointType, string> = {
	complaint: "Complaint",
	letter: "Letter",
	call: "Call",
	message: "Secure message",
	email: "Email",
	branch: "Branch visit",
	transaction: "Transaction",
	card: "Card",
	fee: "Fee",
	payment: "Payment",
	membership: "Membership",
	kyc: "KYC",
	application: "Application",
	delinquency: "Delinquency",
	furnishing: "Bureau furnishing",
	dispute: "Dispute",
	fraud: "Fraud / security",
};
