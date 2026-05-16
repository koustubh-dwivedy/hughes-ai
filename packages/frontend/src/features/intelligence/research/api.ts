/**
 * RTK Query slice for deep-research artefacts (HUG-210, L3).
 *
 * Hooks consumed by:
 *   - PlanPreview (HUG-211)
 *   - StepList (HUG-219, S4)
 *   - ReferencesModal extension (HUG-224, V2)
 *
 * Tag invalidation:
 *   - `useApprovePlanMutation` / `useAbortPlanMutation` invalidate
 *     `ResearchPlan` so the preview re-fetches with the new status.
 *   - SSE events for step.{started,completed,failed} +
 *     plan.revised will dispatch tag invalidations from the
 *     telemetry middleware (HUG-222 wires that in).
 */

import { baseApi } from "../../../shared/api/client";
import type {
	GetFindingsResponse,
	GetLatestPlanResponse,
	GetNotesResponse,
	GetStepsResponse,
	GetSubagentCallsResponse,
	PlanDecisionResponse,
} from "./types";

interface PlanIdentifier {
	threadId: string;
	planId: string;
}

const slice = baseApi.injectEndpoints({
	endpoints: (build) => ({
		getResearchPlan: build.query<GetLatestPlanResponse, string>({
			query: (threadId) => ({
				url: `/threads/${threadId}/plans/latest`,
			}),
			providesTags: (_result, _err, threadId) => [
				{ type: "ResearchPlan", id: threadId },
			],
		}),

		getResearchSteps: build.query<GetStepsResponse, PlanIdentifier>({
			query: ({ threadId, planId }) => ({
				url: `/threads/${threadId}/plans/${planId}/steps`,
			}),
			providesTags: (_result, _err, { planId }) => [
				{ type: "ResearchSteps", id: planId },
			],
		}),

		getResearchFindings: build.query<GetFindingsResponse, PlanIdentifier>({
			query: ({ threadId, planId }) => ({
				url: `/threads/${threadId}/plans/${planId}/findings`,
			}),
			providesTags: (_result, _err, { planId }) => [
				{ type: "ResearchFindings", id: planId },
			],
		}),

		getResearchLeadNotes: build.query<GetNotesResponse, PlanIdentifier>({
			query: ({ threadId, planId }) => ({
				url: `/threads/${threadId}/plans/${planId}/notes`,
			}),
			providesTags: (_result, _err, { planId }) => [
				{ type: "ResearchLeadNotes", id: planId },
			],
		}),

		// HUG-245: subagent_calls rows for the audit panel.
		getResearchSubagentCalls: build.query<
			GetSubagentCallsResponse,
			PlanIdentifier
		>({
			query: ({ threadId, planId }) => ({
				url: `/threads/${threadId}/plans/${planId}/subagent-calls`,
			}),
			providesTags: (_result, _err, { planId }) => [
				{ type: "ResearchSubagentCalls", id: planId },
			],
		}),

		// HUG-247 Phase B + Fix D: /approve route deleted server-side
		// because the autonomous lead agent has no user approval gate.
		// The frontend mutation hook is removed too — calling it would
		// 404. Only /abort survives as a kill-switch.
		abortPlan: build.mutation<PlanDecisionResponse, PlanIdentifier>({
			query: ({ threadId, planId }) => ({
				url: `/threads/${threadId}/plans/${planId}/abort`,
				method: "POST",
			}),
			invalidatesTags: (_result, _err, { threadId }) => [
				{ type: "ResearchPlan", id: threadId },
			],
		}),
	}),
});

export const {
	useGetResearchPlanQuery,
	useGetResearchStepsQuery,
	useGetResearchFindingsQuery,
	useGetResearchLeadNotesQuery,
	useGetResearchSubagentCallsQuery,
	useAbortPlanMutation,
} = slice;

export { slice as researchApi };
