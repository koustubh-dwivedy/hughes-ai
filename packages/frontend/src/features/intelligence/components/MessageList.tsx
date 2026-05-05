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

import OpenUIRenderer from "../openui/OpenUIRenderer";
import JsonBlock from "../../../ui/primitives/JsonBlock/JsonBlock";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import type { ThreadMessageWire } from "../api";

interface Props {
	messages: ThreadMessageWire[];
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

const sectionLabelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	color: colors.slate[600],
	textTransform: "uppercase",
	letterSpacing: "0.04em",
	marginTop: spacing[3],
	marginBottom: spacing[1],
};

const tableWrapStyle: React.CSSProperties = {
	overflowX: "auto",
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	background: colors.white,
	marginTop: spacing[2],
};

const tableStyle: React.CSSProperties = {
	width: "100%",
	borderCollapse: "collapse",
	fontSize: typography.size.xs,
};

const cellStyle: React.CSSProperties = {
	padding: `${spacing[1]} ${spacing[3]}`,
	borderBottom: `1px solid ${colors.slate[100]}`,
	textAlign: "left",
};

const headerCellStyle: React.CSSProperties = {
	...cellStyle,
	background: colors.slate[100],
	fontWeight: typography.weight.medium,
	color: colors.slate[700],
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

function RowsTable({ rows }: { rows: Record<string, unknown>[] }) {
	if (rows.length === 0) return null;
	const cols = Object.keys(rows[0]);
	return (
		<div style={tableWrapStyle}>
			<table style={tableStyle}>
				<thead>
					<tr>
						{cols.map((c) => (
							<th key={c} style={headerCellStyle}>
								{c}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{rows.slice(0, 25).map((r, idx) => (
						// biome-ignore lint/suspicious/noArrayIndexKey: row identity is positional in the agent's tool result
						<tr key={idx}>
							{cols.map((c) => (
								<td key={c} style={cellStyle}>
									{String(r[c] ?? "")}
								</td>
							))}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function AssistantTerminal({ msg }: { msg: ThreadMessageWire }) {
	const payload = parseFinalPayload(msg);
	const summary = payload.summary ?? "";
	return (
		<article aria-label="Assistant answer" style={assistantBubbleStyle}>
			{summary !== "" && <div style={summaryStyle}>{summary}</div>}
			{payload.openui_dsl && payload.openui_dsl.length > 0 ? (
				<div data-testid="openui-renderer">
					<OpenUIRenderer dsl={payload.openui_dsl} />
				</div>
			) : null}
			{payload.rows && payload.rows.length > 0 ? (
				<>
					<div style={sectionLabelStyle}>Source rows</div>
					<RowsTable rows={payload.rows} />
				</>
			) : null}
			{payload.mf_query ? (
				<details>
					<summary
						style={{
							...sectionLabelStyle,
							cursor: "pointer",
							marginBottom: spacing[2],
						}}
					>
						MetricFlow query
					</summary>
					<JsonBlock value={payload.mf_query} label="MetricFlow query" />
				</details>
			) : null}
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

export default function MessageList({ messages }: Props) {
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
				// system messages and intermediate tool calls are not user-visible
				return null;
			})}
		</div>
	);
}
