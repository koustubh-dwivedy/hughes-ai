/**
 * Credit-Bureau Disputes (CBD) domain model — mockup only.
 *
 * Two dispute types are in scope: Validation of Debt (VOD, FDCPA §1692g /
 * Reg F) and Fraud / identity theft (FCRA §605B). Both share a common spine
 * and diverge in a type-specific detail block. All values are fabricated
 * placeholders — no backend, no seed-data linkage.
 */

import type { EvidenceReference } from "./ai/aiTypes";

export type DisputeType = "VOD" | "FRAUD";

/** Metro 2 Compliance Condition Codes surfaced at full fidelity. */
export type Ccc = "XB" | "XC" | "XH" | "XR";

export type Channel = "Direct" | "ACDV" | "CFPB";

export type MatchResult = "Match" | "Mismatch" | "Elevated";

/** Where a Reg F validation-letter field is sourced from. */
export type FieldSource = "LOS" | "core" | "computed";

export interface Member {
	name: string;
	memberNumber: string;
	ssnMasked: string;
	dob: string;
	address: string;
	phone: string;
	email: string;
}

export interface SubjectAccount {
	accountNumberMasked: string;
	productType: string;
	currentBalance: number;
	accountStatus: string;
	openedDate: string;
	dofd: string | null;
	chargeOffDate: string | null;
	reportedBureaus: string[];
}

export interface DisputeCaseBase {
	id: string;
	type: DisputeType;
	/** ACDV control # (null for direct/CFPB-originated cases). */
	acdvNumber: string | null;
	ccc: Ccc | null;
	channel: Channel;
	receivedDate: string;
	slaDueDate: string;
	/** Human-readable status shown in the queue. */
	status: string;
	assignee: string;
	/** Index into the type's stepper stages. */
	currentStage: number;
	member: Member;
	subjectAccount: SubjectAccount;
}

// ---- Validation of Debt -----------------------------------------------------

export interface RegFField {
	label: string;
	value: string;
	source: FieldSource;
}

export interface ValidationDoc {
	label: string;
	source: FieldSource;
	available: boolean;
}

export type VodOutcome =
	| "Validated"
	| "Unable to validate — tradeline deleted"
	| "Corrected";

export interface VodDetail {
	originalCreditor: string;
	currentOwner: string;
	principal: number;
	interest: number;
	fees: number;
	payments: number;
	credits: number;
	itemizationDate: string;
	amountAtItemization: number;
	currentAmount: number;
	disputeWindowEnds: string;
	writtenRequest: boolean;
	withinThirtyDays: boolean;
	collectionHold: boolean;
	/** The auto-assembled Reg F validation letter fields, source-tagged. */
	regFFields: RegFField[];
	validationDocs: ValidationDoc[];
	mailed: boolean;
	mailedDate: string | null;
	mailedMethod: string | null;
	outcome: VodOutcome | null;
}

export interface VodCase extends DisputeCaseBase {
	type: "VOD";
	vod: VodDetail;
}

// ---- Fraud / identity theft -------------------------------------------------

export type FraudSubType =
	| "New-account fraud"
	| "Account takeover"
	| "Fraudulent transactions";

export type TriangulationPillar = "Internal" | "Referential" | "Possession";

/** Where a signal leans on the fraud claim (primary framing). */
export type SignalStance = "supports" | "against" | "inconclusive";

export interface SignalDataPoint {
	label: string;
	value: string;
	/** Visual marker for how this datapoint bears on the call. */
	match?: "match" | "mismatch" | "neutral";
}

export interface TriangulationRow {
	pillar: TriangulationPillar;
	/** Real vendor / system name, e.g. "LexisNexis InstantID", "Prove". */
	source: string;
	signal: string;
	/** Raw vendor result (secondary detail). */
	result: MatchResult;
	/** Primary framing — what this signal argues about the fraud claim. */
	stance: SignalStance;
	/** (a) The agent's non-deterministic exploration / how it resolved ambiguity. */
	resolution: string;
	/** Raw datapoints behind the call, for the human to validate. */
	dataPoints: SignalDataPoint[];
	/** Optional cited evidence (inline preview, external link, or asset overlay). */
	reference?: EvidenceReference;
}

export interface IdentityTheftReport {
	onFile: boolean;
	type: "FTC Identity Theft Report" | "Police report" | null;
	referenceNumber: string | null;
	jurisdiction: string | null;
	receivedDate: string | null;
}

export type FraudDecision =
	| "Third-party (confirmed)"
	| "First-party (no fraud)";

export type FraudOutcome =
	| "Blocked & suppressed (§605B)"
	| "Denied — first-party";

export interface FraudCrossRefs {
	sarReferral: boolean;
	cardReissue: boolean;
	linkedAccounts: string[];
}

export interface FraudDetail {
	subType: FraudSubType;
	identityTheftReport: IdentityTheftReport;
	fraudAlert: boolean;
	triangulation: TriangulationRow[];
	blockBusinessDaysRemaining: number;
	blockApplied: boolean;
	preventRefurnish: boolean;
	collectionProhibition: boolean;
	decision: FraudDecision | null;
	crossRefs: FraudCrossRefs;
	outcome: FraudOutcome | null;
}

export interface FraudCase extends DisputeCaseBase {
	type: "FRAUD";
	fraud: FraudDetail;
}

export type DisputeCase = VodCase | FraudCase;

// ---- Stepper stages (distinct per type) -------------------------------------

export const VOD_STAGES = [
	"Intake",
	"Triage",
	"Assemble verification",
	"Mail",
	"Report",
	"Close",
] as const;

export const FRAUD_STAGES = [
	"Intake",
	"Triangulate & decide",
	"Suppress & block (§605B)",
	"Close",
] as const;

export function stagesFor(type: DisputeType): readonly string[] {
	return type === "VOD" ? VOD_STAGES : FRAUD_STAGES;
}
