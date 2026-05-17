/**
 * Persistent message history for a single thread. Reads from the RTK
 * Query cache (`useGetThreadQuery`); the in-flight SSE step list lives
 * in `threadSlice` and renders via `<StepIndicator>` separately.
 * Tool messages from `final_answer` carry the rich payload (OpenUI DSL,
 * mf_query, rows); persisted columns take precedence, falling back to
 * the JSON `content` blob.
 */
import { useState } from "react";
import { useAppSelector } from "../../../shared/api/hooks";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { ThreadMessageWire } from "../api";
import OpenUIRenderer from "../openui/OpenUIRenderer";
import { useGetResearchPlanQuery } from "../research/api";
import {
	selectCurrentStream,
	selectIsStreamingOnCurrentThread,
} from "../threadSelectors";
import MarkdownText from "./MarkdownText";
import ReferencesModal from "./ReferencesModal";

interface Props {
	messages: ThreadMessageWire[];
	/** Optimistic user-question bubble shown at the tail while the agent is
	 *  responding (HUG-201 option A). Cleared once the persisted history
	 *  refetches with the matching user message. */
	pendingUserContent?: string | null;
}

interface FinalPayload {
	summary?: string;
	openui_dsl?: string | null;
	mf_query?: Record<string, unknown> | null;
	rows?: Record<string, unknown>[] | null;
	thinking_trace?: import("../api").ThreadTraceEntry[] | null;
}

const containerStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	gap: spacing[3],
	padding: spacing[3],
};

const userBubbleStyle: React.CSSProperties = {
	alignSelf: "flex-end",
	maxWidth: "80%",
	background: colors.indigo[700],
	color: colors.white,
	padding: `${spacing[2]} ${spacing[3]}`,
	borderRadius: radii.lg,
	fontSize: typography.size.sm,
};

const assistantBubbleStyle: React.CSSProperties = {
	alignSelf: "flex-start",
	maxWidth: "92%",
	background: colors.slate[50],
	color: colors.slate[800],
	padding: spacing[3],
	borderRadius: radii.lg,
	border: `1px solid ${colors.slate[200]}`,
	fontSize: typography.size.sm,
};

const summaryStyle: React.CSSProperties = {
	fontSize: typography.size.base,
	lineHeight: 1.5,
	marginBottom: spacing[2],
};

function parseFinalPayload(msg: ThreadMessageWire): FinalPayload {
	// `summary` only lives inside the content JSON blob; dedicated
	// columns take precedence for the rich fields when populated.
	let blob: FinalPayload = {};
	if (msg.content) {
		try {
			blob = JSON.parse(msg.content) as FinalPayload;
		} catch {
			blob = {};
		}
	}
	return {
		summary: blob.summary,
		openui_dsl: msg.openui_dsl ?? blob.openui_dsl ?? null,
		mf_query: msg.mf_query ?? blob.mf_query ?? null,
		rows: msg.rows ?? blob.rows ?? null,
		thinking_trace: msg.thinking_trace ?? blob.thinking_trace ?? null,
	};
}

function isFinalAnswerToolMessage(msg: ThreadMessageWire): boolean {
	if (msg.role !== "tool") return false;
	const results = msg.tool_results;
	if (!results || results.length === 0) return false;
	const first = results[0] as { name?: string };
	return first.name === "final_answer";
}

const referencesPillStyle: React.CSSProperties = {
	alignSelf: "flex-start",
	marginTop: spacing[2],
	background: colors.white,
	color: colors.indigo[700],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	padding: `${spacing[1]} ${spacing[3]}`,
	cursor: "pointer",
	fontSize: typography.size.xs,
	fontFamily: typography.fontFamily,
	fontWeight: typography.weight.medium,
	display: "inline-flex",
	alignItems: "center",
	gap: spacing[1],
};

function ReferencesSection({
	payload,
	threadId,
}: {
	payload: FinalPayload;
	threadId: string;
}) {
	const [open, setOpen] = useState(false);
	const rows = payload.rows ?? null;
	const mfQuery = payload.mf_query ?? null;
	const trace = payload.thinking_trace ?? null;
	const count = (rows?.length ?? 0) + (mfQuery ? 1 : 0) + (trace?.length ?? 0);
	// Lazy-fetch the latest plan so the audit panel can render per-worker
	// mf_queries when this is a deep-research answer. Skipped until open.
	const { data: planResp } = useGetResearchPlanQuery(threadId, { skip: !open });
	const researchPlanId = planResp?.plan?.plan_id ?? undefined;
	if (count === 0) return null;
	return (
		<>
			<button
				type="button"
				style={referencesPillStyle}
				onClick={() => setOpen(true)}
				aria-haspopup="dialog"
				data-testid="references-button"
			>
				<span aria-hidden>📎</span>
				References ({count})
			</button>
			<ReferencesModal
				open={open}
				onClose={() => setOpen(false)}
				rows={rows}
				mfQuery={mfQuery}
				thinkingTrace={trace}
				researchPlanId={researchPlanId}
				researchThreadId={researchPlanId ? threadId : undefined}
			/>
		</>
	);
}

function AssistantTerminal({ msg }: { msg: ThreadMessageWire }) {
	const payload = parseFinalPayload(msg);
	const summary = payload.summary ?? "";
	const dsl = payload.openui_dsl;
	return (
		<article
			aria-label="Assistant answer"
			data-testid="final-answer"
			style={assistantBubbleStyle}
		>
			{summary !== "" && (
				<div data-testid="final-summary">
					<MarkdownText style={summaryStyle}>{summary}</MarkdownText>
				</div>
			)}
			{dsl && dsl.length > 0 ? (
				<div data-testid="openui-renderer">
					<OpenUIRenderer dsl={dsl} />
				</div>
			) : null}
			<ReferencesSection payload={payload} threadId={msg.thread_id} />
		</article>
	);
}

const streamingCaretStyle: React.CSSProperties = {
	display: "inline-block",
	width: 8,
	height: "1em",
	verticalAlign: "text-bottom",
	background: colors.slate[500],
	marginLeft: 2,
	animation: "hughesStreamingCaret 1s step-end infinite",
};

const STREAMING_CARET_KEYFRAMES_ID = "hughes-streaming-caret-keyframes";

function ensureCaretKeyframes(): void {
	if (typeof document === "undefined") return;
	if (document.getElementById(STREAMING_CARET_KEYFRAMES_ID)) return;
	const style = document.createElement("style");
	style.id = STREAMING_CARET_KEYFRAMES_ID;
	style.textContent = `
@keyframes hughesStreamingCaret {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
`;
	document.head.appendChild(style);
}

/** In-flight assistant bubble fed by the current thread's
 *  `streamingSummary` slot. Replaced by the persisted AssistantTerminal
 *  as soon as the thread-cache refetch lands (HUG-202 Phase 2). */
function StreamingAssistant() {
	const text = useAppSelector((s) => selectCurrentStream(s).streamingSummary);
	if (!text) return null;
	ensureCaretKeyframes();
	return (
		<article
			aria-label="Assistant answer (streaming)"
			style={assistantBubbleStyle}
		>
			<div data-testid="streaming-summary">
				<MarkdownText style={summaryStyle}>{text}</MarkdownText>
				<span style={streamingCaretStyle} aria-hidden />
			</div>
		</article>
	);
}

function UserBubble({ msg }: { msg: ThreadMessageWire }) {
	return (
		<div style={userBubbleStyle} aria-label="User question">
			{msg.content ?? ""}
		</div>
	);
}

function AssistantText({ msg }: { msg: ThreadMessageWire }) {
	if (!msg.content) return null;
	// Intermediate reasoning the LLM emits alongside a tool call ("I
	// found the metric, now let me probe for the date…") is NOT a
	// final user-facing answer. It's part of the agent's chain-of-
	// thought and lives in the Thinking trace via the References pill.
	// Hide it from the chat so the conversation stays clean.
	if (msg.tool_calls && msg.tool_calls.length > 0) return null;
	return (
		<article aria-label="Assistant message" style={assistantBubbleStyle}>
			<MarkdownText style={summaryStyle}>{msg.content}</MarkdownText>
		</article>
	);
}

export default function MessageList({ messages, pendingUserContent }: Props) {
	// Live state for the currently-viewed thread only — the slot is
	// per-thread, so concurrent streams on other threads don't bleed in.
	const liveOnThisThread = useAppSelector(selectIsStreamingOnCurrentThread);
	const currentStream = useAppSelector(selectCurrentStream);
	const streamingSummary = currentStream.streamingSummary;
	// Find the last persisted final-answer tool message — when it
	// matches the streaming summary's content, switch from the in-flight
	// bubble to the persisted one to avoid double-render.
	const persistedHasMatchingTerminal = (() => {
		for (let i = messages.length - 1; i >= 0; i--) {
			const m = messages[i];
			if (m.role === "tool" && isFinalAnswerToolMessage(m)) return true;
		}
		return false;
	})();
	const showStreamingBubble =
		liveOnThisThread ||
		(streamingSummary.length > 0 && !persistedHasMatchingTerminal);
	return (
		<div style={containerStyle} role="log" aria-live="polite">
			{messages.map((msg) => {
				if (msg.role === "user") {
					return <UserBubble key={msg.message_id} msg={msg} />;
				}
				if (msg.role === "assistant") {
					return <AssistantText key={msg.message_id} msg={msg} />;
				}
				if (msg.role === "tool" && isFinalAnswerToolMessage(msg)) {
					return <AssistantTerminal key={msg.message_id} msg={msg} />;
				}
				return null;
			})}
			{pendingUserContent ? (
				<div style={userBubbleStyle} aria-label="User question (sending)">
					{pendingUserContent}
				</div>
			) : null}
			{showStreamingBubble ? <StreamingAssistant /> : null}
		</div>
	);
}
