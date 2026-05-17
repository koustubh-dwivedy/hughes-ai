/**
 * Research-lifecycle SSE event dispatch (HUG-222, M3 + Bug 4, 2026-05-17).
 *
 * Pulled out of `intelligence/api.ts` to keep that file under the
 * 300-line structural cap. When the chat SSE stream emits a
 * `research.plan.*` or `research.subagent.*` event:
 *   - invalidate RTK Query tags so PlanPreview + audit panel refetch
 *   - dispatch live-activity slice actions so ThinkingBubble can show
 *     the lead's in-flight plan + subagent state
 */

import { baseApi } from "../../shared/api/client";
import {
	streamPlanDrafted,
	streamSubagentCompleted,
	streamSubagentFailed,
	streamSubagentSpawned,
} from "./threadSlice";

export const RESEARCH_PLAN_EVENTS = new Set([
	"research.plan.drafted",
	"research.plan.approved",
	"research.plan.aborted",
	"research.plan.revised",
]);

export const RESEARCH_SUBAGENT_EVENTS = new Set([
	"research.subagent.spawned",
	"research.subagent.completed",
	"research.subagent.failed",
]);

type Dispatch = (a: { type: string; payload?: unknown }) => unknown;

export function dispatchResearchPlanInvalidation(
	dispatch: Dispatch,
	parsed: unknown,
): void {
	const payload = parsed as { thread_id?: string; plan_id?: string };
	const tags: Array<{ type: "ResearchPlan" | "ResearchSteps"; id: string }> =
		[];
	if (payload.thread_id)
		tags.push({ type: "ResearchPlan", id: payload.thread_id });
	if (payload.plan_id)
		tags.push({ type: "ResearchSteps", id: payload.plan_id });
	if (tags.length === 0) return;
	dispatch(
		baseApi.util.invalidateTags(tags) as unknown as {
			type: string;
			payload?: unknown;
		},
	);
}

export function dispatchLivePlan(dispatch: Dispatch, parsed: unknown): void {
	const p = parsed as {
		plan_id: string;
		version: number;
		plan_json?: { plan?: unknown[] };
	};
	dispatch(
		streamPlanDrafted({
			plan_id: p.plan_id,
			version: p.version,
			step_count: p.plan_json?.plan?.length ?? 0,
		}),
	);
}

export function dispatchSubagentEvent(
	dispatch: Dispatch,
	event: string,
	parsed: unknown,
): void {
	if (event === "research.subagent.spawned") {
		const p = parsed as { call_id: string; prompt: string };
		dispatch(streamSubagentSpawned({ call_id: p.call_id, prompt: p.prompt }));
	} else if (event === "research.subagent.completed") {
		const p = parsed as { call_id: string };
		dispatch(streamSubagentCompleted({ call_id: p.call_id }));
	} else if (event === "research.subagent.failed") {
		const p = parsed as { call_id: string; error?: string };
		dispatch(
			streamSubagentFailed({ call_id: p.call_id, error: p.error ?? "failed" }),
		);
	}
}
