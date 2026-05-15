/**
 * Research-lifecycle SSE event dispatch (HUG-222, M3).
 *
 * Pulled out of `intelligence/api.ts` to keep that file under the
 * 300-line structural cap. When the chat SSE stream emits a
 * `research.plan.*` event, dispatch the matching RTK Query tag
 * invalidations so PlanPreview / StepList refetch.
 */

import { baseApi } from "../../shared/api/client";

export const RESEARCH_PLAN_EVENTS = new Set([
	"research.plan.drafted",
	"research.plan.approved",
	"research.plan.aborted",
	"research.plan.revised",
]);

type Dispatch = (a: { type: string; payload?: unknown }) => unknown;

export function dispatchResearchPlanInvalidation(
	dispatch: Dispatch,
	parsed: unknown,
): void {
	const payload = parsed as { thread_id?: string; plan_id?: string };
	const tags: Array<{
		type: "ResearchPlan" | "ResearchSteps";
		id: string;
	}> = [];
	if (payload.thread_id) {
		tags.push({ type: "ResearchPlan", id: payload.thread_id });
	}
	if (payload.plan_id) {
		tags.push({ type: "ResearchSteps", id: payload.plan_id });
	}
	if (tags.length === 0) return;
	dispatch(
		baseApi.util.invalidateTags(tags) as unknown as {
			type: string;
			payload?: unknown;
		},
	);
}
