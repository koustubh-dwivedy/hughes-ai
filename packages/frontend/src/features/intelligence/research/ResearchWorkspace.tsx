/**
 * Research-workspace shell (HUG-211, L4).
 *
 * Decides what to render under the chat when a research plan exists
 * for the active thread:
 *   - `status='draft'` → PlanPreview (the user must approve to run).
 *   - `status='approved'/'running'/'complete'` → StepList placeholder
 *     (HUG-219, S4 implements it).
 *   - No plan → returns null (chat-only thread).
 *
 * Consumed by IntelligencePage when a thread is active.
 */

import PlanPreview from "./PlanPreview";
import StepList from "./StepList";
import { useGetResearchPlanQuery } from "./api";

interface Props {
	threadId: string;
}

export default function ResearchWorkspace({ threadId }: Props) {
	const { data, isLoading } = useGetResearchPlanQuery(threadId);
	if (isLoading) return null;
	const plan = data?.plan;
	if (!plan) return null;
	if (plan.status === "draft") return <PlanPreview plan={plan} />;
	// HUG-219 (S4): full step list once the plan is approved.
	return <StepList threadId={plan.thread_id} planId={plan.plan_id} />;
}
