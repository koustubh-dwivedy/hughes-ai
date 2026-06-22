/**
 * AI human-in-the-loop layer for the Dispute Center (mockup).
 *
 * The mockup distinguishes deterministic steps from AI-assisted / agentic ones
 * and renders the agent's recommendation, reasoning, and cited evidence so a
 * human associate can approve / override / request more info. All AI artifacts
 * are fabricated placeholders shaped to a real contract — no LLM/vendor calls,
 * and the "agent" never mutates case state (evidence-gathering only).
 */

export type AiProvenance = "deterministic" | "ai_assisted" | "agentic";

export type EvidenceRefType = "api_record" | "document" | "call_recording";

/** A mockable in-app file asset a reference can open in a blurred overlay. */
export type AssetKind =
	| "letter"
	| "statement"
	| "cfpb_complaint"
	| "call_transcript"
	| "dispute_letter"
	| "ftc_id_theft_report"
	| "acdv";

export interface EvidenceReference {
	type: EvidenceRefType;
	label: string;
	/** External link when the source is web-reachable. */
	url?: string;
	/** Internal pointer when there's no link (e.g. a call recording). */
	locator?: string;
	/** Short inline preview shown on hover. */
	preview?: string;
	/** When set, the reference opens this mocked file asset in an overlay. */
	asset?: { kind: AssetKind; title?: string };
}

export type CheckStatus = "pass" | "fail" | "n_a";

export interface DeterministicCheck {
	check: string;
	status: CheckStatus;
	basis: string;
}

export type ReasoningKind = "tool_call" | "tool_result" | "thinking";

export interface ReasoningStep {
	kind: ReasoningKind;
	label: string;
	detail?: string;
}

export type AiConfidence = "low" | "medium" | "high";

export type Recommendation =
	| "block_605b"
	| "deny_first_party"
	| "validate"
	| "unable_to_validate"
	| "needs_more_info";

export type HumanAction = "approved" | "overridden" | "more_info";

/** The agentic Investigation result (fraud triangulation / VOD close rec). */
export interface AiInvestigation {
	recommendation: Recommendation;
	/** Human-readable label, e.g. "Block tradeline (§605B)". */
	recommendationLabel: string;
	confidence: AiConfidence;
	rationale: string;
	/** Computed checks — kept separate from reasoned evidence. */
	deterministicChecks: DeterministicCheck[];
	reasoning: ReasoningStep[];
}

export type SorMatchResult = "matched" | "partial" | "mismatch";

export interface SorComparison {
	field: string;
	received: string;
	sor: string;
	match: "match" | "mismatch" | "partial";
}

/**
 * AI reconciliation of the inbound dispute against the system of record — the
 * core reason AI is needed at intake: confirm the received application matches
 * the member/account we have on file.
 */
export interface SorMatch {
	result: SorMatchResult;
	confidence: AiConfidence;
	comparisons: SorComparison[];
}

/** AI handling of an unstructured intake document: SOR match + extracted fields. */
export interface IntakeExtraction {
	fields: { label: string; value: string }[];
	sourceDoc: EvidenceReference;
	confidence: AiConfidence;
	/** Received-vs-system-of-record identity match (VOD intake). */
	sorMatch?: SorMatch;
}

/** AI completeness/consistency QA of the VOD validation package. */
export interface ValidationQa {
	complete: boolean;
	discrepancies: string[];
	recommendation: Recommendation;
	recommendationLabel: string;
	confidence: AiConfidence;
}

export interface CaseAi {
	intake?: IntakeExtraction;
	investigation?: AiInvestigation;
	validationQa?: ValidationQa;
}

/**
 * Per-stage provenance, indexed to match VOD_STAGES / FRAUD_STAGES in
 * `../types`. Drives the provenance badge on each stepper stage.
 */
export const VOD_PROVENANCE: AiProvenance[] = [
	"ai_assisted", // Intake — extract from letter/CFPB narrative
	"deterministic", // Verify request — date math + channel
	"deterministic", // Assemble package — LOS+core pull + template
	"deterministic", // Mail
	"deterministic", // Report — Metro 2 rule
	"ai_assisted", // Close — validation QA + recommendation
];

export const FRAUD_PROVENANCE: AiProvenance[] = [
	"ai_assisted", // Intake — extract Identity-Theft-Report fields
	"agentic", // Triangulate & decide — orchestrate evidence + human sign-off
	"deterministic", // Suppress & block (§605B)
	"deterministic", // Close
];

export const PROVENANCE_LABEL: Record<AiProvenance, string> = {
	deterministic: "Deterministic",
	ai_assisted: "AI-assisted",
	agentic: "Agentic AI",
};

export const CONFIDENCE_LABEL: Record<AiConfidence, string> = {
	low: "Low confidence",
	medium: "Medium confidence",
	high: "High confidence",
};
