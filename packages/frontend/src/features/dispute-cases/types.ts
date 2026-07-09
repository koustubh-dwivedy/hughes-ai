/**
 * Credit-Bureau Disputes (CBD) domain model — mockup only.
 *
 * Two dispute types are in scope: ACDV data-accuracy / field-comparison
 * disputes (FCRA §1681s-2(b) furnisher investigation — the deterministic
 * automation core) and Fraud / identity theft (FCRA §605B). Both share a
 * common spine and diverge in a type-specific detail block. All values are
 * fabricated placeholders — no backend, no seed-data linkage.
 */

import type { AssetKind, EvidenceReference } from "./ai/aiTypes";
import type { ReasonCode, ResponseCode } from "./codes";

export type { DisputeCategory, ReasonCode, ResponseCode } from "./codes";
export {
	categoryForReason,
	DISPUTE_CATEGORY,
	REASON_CODE_LABEL,
	RESPONSE_CODE_LABEL,
} from "./codes";

export type DisputeType = "FRAUD" | "DATA_ACCURACY";

/** Metro 2 Compliance Condition Codes surfaced at full fidelity. */
export type Ccc = "XB" | "XC" | "XH" | "XR";

/** How the dispute reached the furnisher: an e-OSCAR ACDV or a direct request. */
export type Channel = "Direct" | "eOSCAR";

export type MatchResult = "Match" | "Mismatch" | "Elevated";

/** Where a field value is sourced from. */
export type FieldSource = "LOS" | "core" | "computed";

// ---- ACDV attachments (consumer images pushed by e-OSCAR) -------------------

export type AttachmentFileType = "TIFF" | "JPG" | "GIF" | "PNG" | "PDF";

/**
 * A document the CRA pushed alongside the ACDV. Consumer images are the single
 * strongest human-review trigger; the furnisher must take at least one action
 * (View/Print/Download) on each — modeled by `acknowledged`.
 */
export interface AcdvAttachment {
	kind: AssetKind;
	fileName: string;
	fileType: AttachmentFileType;
	label: string;
	/** Furnisher took a View/Print/Download action. Starts false for images. */
	acknowledged: boolean;
}

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
	/** Consumer images / documents pushed with the ACDV (default empty). */
	attachments: AcdvAttachment[];
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
	/** e-OSCAR dispute reason code (103 identity fraud / 104 account takeover). */
	reasonCode: ReasonCode;
	/** Recommended e-OSCAR response (07 delete-for-fraud / 01 verify if first-party). */
	recommendedResponse: ResponseCode;
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

// ---- ACDV data-accuracy / field-comparison ----------------------------------

/** One disputed Metro 2 field: ACDV "as reported" vs the core system of record. */
export interface FieldComparison {
	field: string;
	asReported: string;
	systemOfRecord: string;
	match: "match" | "mismatch";
}

/**
 * The three autonomy gates from the research. All must clear for the agent to
 * act autonomously; any tripped gate routes the case to a human.
 */
export interface AutonomyGates {
	/** A consumer image is attached (trips the gate). */
	imageAttached: boolean;
	/** Free-text contradicts or expands the numeric code (trips the gate). */
	freeTextConflict: boolean;
	/** The core field is populated and Metro 2-consistent (must be true). */
	fieldPopulatedConsistent: boolean;
}

export function gatesPass(g: AutonomyGates): boolean {
	return !g.imageAttached && !g.freeTextConflict && g.fieldPopulatedConsistent;
}

export type DataAccuracyOutcome =
	| "Verified as reported"
	| "Corrected & refurnished"
	| "Field deleted"
	| "Verified (non-specific)";

export interface DataAccuracyDetail {
	reasonCode: ReasonCode;
	/** "Date of Account Information" the comparison is made as of. */
	dateOfAccountInfo: string;
	disputedFields: FieldComparison[];
	gates: AutonomyGates;
	recommendedResponse: ResponseCode;
	/**
	 * Whether the agent may resolve straight-through. Usually `gatesPass`, but a
	 * correction that would flip derogatory↔positive is drafted even if gates
	 * clear — so this is stored, not derived.
	 */
	autonomyMode: "autonomous" | "draft_for_human";
	freeText: string | null;
	outcome: DataAccuracyOutcome | null;
}

export interface DataAccuracyCase extends DisputeCaseBase {
	type: "DATA_ACCURACY";
	dataAccuracy: DataAccuracyDetail;
}

export type DisputeCase = FraudCase | DataAccuracyCase;

// ---- Stepper stages (distinct per type) -------------------------------------

export const FRAUD_STAGES = [
	"Intake",
	"Triangulate & decide",
	"Suppress & block (§605B)",
	"Close",
] as const;

export const DATA_ACCURACY_STAGES = [
	"Intake",
	"Compare fields",
	"Decide response",
	"Report",
	"Close",
] as const;

export function stagesFor(type: DisputeType): readonly string[] {
	return type === "FRAUD" ? FRAUD_STAGES : DATA_ACCURACY_STAGES;
}
