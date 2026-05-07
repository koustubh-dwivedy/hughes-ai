/**
 * Persistent message history for a single thread (HUG-179).
 *
 * Reads from the RTK Query cache (`useGetThreadQuery`) — the source of
 * truth for everything that's been written to `thread_messages`. The
 * in-flight SSE step list lives in `threadSlice` and is rendered by
 * <StepIndicator> separately; here we only show what's been persisted.
 *
 * Tool messages from `final_answer` carry the rich payload (OpenUI DSL,
 * MetricFlow query, source rows). When the persisted columns are
 * populated we use them directly; when they're empty (older threads or
 * if the runner doesn't thread the fields through) we fall back to
 * parsing the JSON `content` blob.
 */

import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { ThreadMessageWire } from "../api";
import OpenUIRenderer from "../openui/OpenUIRenderer";
import ReferencesModal from "./ReferencesModal";
import TypewriterText from "./TypewriterText";

interface Props {
	messages: ThreadMessageWire[];
	/** The id of the most-recently-arrived final-answer ToolMessage, so the
	 *  summary types-in once instead of every re-render. */
	animatedTerminalId?: string | null;
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
	// `summary` only lives inside the content JSON blob — the
	// persistence layer doesn't have a dedicated column for it. Parse
	// the blob first so we always have access to it, then prefer the
	// dedicated columns for the rich fields when populated.
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

function AssistantTerminal({
	msg,
	animate,
}: {
	msg: ThreadMessageWire;
	animate: boolean;
}) {
	const payload = parseFinalPayload(msg);
	const summary = payload.summary ?? "";
	const [showRefs, setShowRefs] = useState(false);
	const hasRows = (payload.rows?.length ?? 0) > 0;
	const hasMfQuery = payload.mf_query !== null && payload.mf_query !== undefined;
	const hasReferences = hasRows || hasMfQuery;
	const refCount = (payload.rows?.length ?? 0) + (hasMfQuery ? 1 : 0);
	return (
		<article aria-label="Assistant answer" style={assistantBubbleStyle}>
			{summary !== "" && (
				<div style={summaryStyle}>
					{animate ? <TypewriterText text={summary} /> : summary}
				</div>
			)}
			{payload.openui_dsl && payload.openui_dsl.length > 0 ? (
				<div data-testid="openui-renderer">
					<OpenUIRenderer dsl={payload.openui_dsl} />
				</div>
			) : null}
			{hasReferences ? (
				<button
					type="button"
					style={referencesPillStyle}
					onClick={() => setShowRefs(true)}
					aria-haspopup="dialog"
				>
					<span aria-hidden>📎</span>
					References ({refCount})
				</button>
			) : null}
			<ReferencesModal
				open={showRefs}
				onClose={() => setShowRefs(false)}
				rows={payload.rows ?? null}
				mfQuery={payload.mf_query ?? null}
			/>
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
	return (
		<article aria-label="Assistant message" style={assistantBubbleStyle}>
			<div style={summaryStyle}>{msg.content}</div>
		</article>
	);
}

export default function MessageList({
	messages,
	animatedTerminalId,
	pendingUserContent,
}: Props) {
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
					return (
						<AssistantTerminal
							key={msg.message_id}
							msg={msg}
							animate={animatedTerminalId === msg.message_id}
						/>
					);
				}
				// system messages and intermediate tool calls are not user-visible
				return null;
			})}
			{pendingUserContent ? (
				<div style={userBubbleStyle} aria-label="User question (sending)">
					{pendingUserContent}
				</div>
			) : null}
		</div>
	);
}
