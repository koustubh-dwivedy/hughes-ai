/**
 * Live "agent is thinking" indicator (HUG-179).
 *
 * Reads the in-flight SSE step list from `threadSlice` and translates
 * each tool-call kind into a human label. Only shown while the slice's
 * `streaming` flag is true; the persisted history takes over after the
 * final event lands.
 */

import { useAppSelector } from "../../../shared/api/hooks";
import { colors, spacing, typography } from "../../../theme/tokens";
import type { ThreadStreamStep } from "../threadSlice";

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	gap: spacing[1],
	color: colors.slate[600],
	fontSize: typography.size.sm,
	fontStyle: "italic",
};

const dotStyle: React.CSSProperties = {
	display: "inline-block",
	width: 6,
	height: 6,
	borderRadius: "50%",
	background: colors.slate[500],
	marginRight: spacing[2],
};

function labelForStep(step: ThreadStreamStep): string {
	if (step.kind === "tool_call") {
		switch (step.name) {
			case "list_metrics":
				return "Looking up available metrics…";
			case "lookup_metric_definition":
				return "Reading the metric definition…";
			case "mf_query":
				return "Querying MetricFlow…";
			case "clarify":
				return "Drafting a clarification question…";
			case "final_answer":
				return "Drafting the answer…";
			default:
				return `Calling ${step.name ?? "tool"}…`;
		}
	}
	if (step.kind === "tool_result") return "Got results.";
	if (step.kind === "thinking") return "Thinking…";
	return step.kind;
}

export default function StepIndicator() {
	const streaming = useAppSelector((s) => s.thread.streaming);
	const streamingThreadId = useAppSelector((s) => s.thread.streamingThreadId);
	const currentThreadId = useAppSelector((s) => s.thread.currentThreadId);
	const steps = useAppSelector((s) => s.thread.steps);
	// Same per-thread gate as ThinkingBubble — don't leak A's step
	// indicator onto B when the user switches mid-stream.
	const liveOnThisThread = streaming && streamingThreadId === currentThreadId;
	if (!liveOnThisThread && steps.length === 0) return null;
	if (steps.length === 0) return null;
	return (
		<output aria-live="polite" style={wrapperStyle}>
			{steps.map((step) => (
				<div key={`${step.step}-${step.kind}`}>
					<span style={dotStyle} aria-hidden />
					{labelForStep(step)}
				</div>
			))}
		</output>
	);
}
