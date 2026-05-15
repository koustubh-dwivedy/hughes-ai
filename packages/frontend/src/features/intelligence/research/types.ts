/**
 * TypeScript mirrors of `api.types.research` Pydantic models
 * (HUG-210, L3).
 *
 * Mirrors the four typed objects landed in HUG-203:
 *   - Plan
 *   - Step
 *   - Finding
 *   - LeadNote
 *
 * The JSON schemas in
 * `packages/frontend/src/shared/api/schemas/research.json` are the
 * canonical contract; the type-drift gate (HUG-232) catches any
 * silent divergence between this file and Pydantic.
 *
 * Status enums mirror the Literal types in research.py.
 */

export type PlanStatus =
	| "draft"
	| "approved"
	| "running"
	| "complete"
	| "aborted"
	| "failed"
	| "superseded";

export type StepStatus =
	| "pending"
	| "running"
	| "complete"
	| "failed"
	| "skipped";

export interface Plan {
	plan_id: string;
	thread_id: string;
	version: number;
	status: PlanStatus;
	plan_json: PlanJson;
	created_at: string;
}

/** Shape of `plan_json` — the planner's PlanDraft serialized. */
export interface PlanJson {
	route: "shallow" | "deep";
	reason: string;
	plan: PlanStepDescriptor[] | null;
	research_question_summary?: string;
}

export interface PlanStepDescriptor {
	ordinal: number;
	description: string;
	dependencies: number[];
}

export interface Step {
	step_id: string;
	plan_id: string;
	ordinal: number;
	description: string;
	status: StepStatus;
	assigned_subagent: string | null;
	started_at: string | null;
	completed_at: string | null;
}

export interface Finding {
	finding_id: string;
	step_id: string;
	summary_text: string | null;
	structured_rows_json: Array<Record<string, unknown>> | null;
	mf_query_json: Record<string, unknown> | null;
	cited_artifacts: Array<Record<string, unknown>> | null;
	created_at: string;
}

export interface LeadNote {
	note_id: string;
	plan_id: string;
	version: number;
	body_md: string;
	created_at: string;
}

/** API response envelopes (one field per resource). */
export interface GetLatestPlanResponse {
	plan: Plan | null;
}

export interface GetStepsResponse {
	steps: Step[];
}

export interface GetFindingsResponse {
	findings: Finding[];
}

export interface GetNotesResponse {
	notes: LeadNote[];
}

/** Approve/abort POST response is the SSE event envelope: `{event, data}`. */
export interface PlanDecisionResponse {
	event: "research.plan.approved" | "research.plan.aborted";
	data: string;
}
