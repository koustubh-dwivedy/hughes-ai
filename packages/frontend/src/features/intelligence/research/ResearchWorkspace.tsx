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
	// Placeholder for HUG-219 (S4 — frontend parallel step display).
	// Today we render a minimal status pill so the user sees execution
	// is in progress; HUG-219 replaces with the full step list UI.
	return (
		<aside
			aria-label="Research execution status"
			style={{
				padding: "8px 12px",
				borderTop: "1px solid #e2e8f0",
				fontSize: 13,
				color: "#475569",
			}}
		>
			Research plan v{plan.version} — status: {plan.status}.
		</aside>
	);
}
