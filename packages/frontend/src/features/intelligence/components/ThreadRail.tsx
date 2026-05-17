/**
 * Collapsible thread rail (HUG-179).
 *
 * Lists the user's recent threads via `useListThreadsQuery` and lets
 * them open one or start a new conversation. The rail is purely
 * navigational — it doesn't display message content. Active thread is
 * highlighted via the `currentThreadId` prop (passed in from the page
 * because the rail is rendered next to the messages and the page
 * already reads `currentThreadId`).
 */

import { Link } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { useListThreadsQuery } from "../api";

interface Props {
	currentThreadId: string | null;
	onNewThread: () => void;
}

const wrapperStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	width: 240,
	flexShrink: 0,
	background: colors.slate[50],
	borderRight: `1px solid ${colors.slate[200]}`,
	padding: spacing[2],
	gap: spacing[1],
	overflowY: "auto",
};

const newButtonStyle: React.CSSProperties = {
	background: colors.indigo[700],
	color: colors.white,
	border: "none",
	borderRadius: radii.md,
	padding: `${spacing[2]} ${spacing[3]}`,
	cursor: "pointer",
	fontSize: typography.size.sm,
	fontWeight: typography.weight.medium,
	fontFamily: typography.fontFamily,
	marginBottom: spacing[2],
};

function rowStyle(active: boolean): React.CSSProperties {
	return {
		display: "block",
		padding: `${spacing[2]} ${spacing[3]}`,
		borderRadius: radii.sm,
		fontSize: typography.size.sm,
		color: active ? colors.indigo[700] : colors.slate[700],
		background: active ? colors.white : "transparent",
		border: active ? `1px solid ${colors.slate[200]}` : "1px solid transparent",
		textDecoration: "none",
		whiteSpace: "nowrap",
		overflow: "hidden",
		textOverflow: "ellipsis",
		fontWeight: active ? typography.weight.medium : typography.weight.normal,
	};
}

const headingStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.04em",
	fontWeight: typography.weight.medium,
	marginTop: spacing[2],
	marginBottom: spacing[1],
	padding: `0 ${spacing[3]}`,
};

const emptyStyle: React.CSSProperties = {
	padding: spacing[3],
	color: colors.slate[500],
	fontSize: typography.size.xs,
	fontStyle: "italic",
};

function formatTitle(threadId: string, title: string | null): string {
	if (title && title.trim().length > 0) return title;
	return `Thread ${threadId.slice(0, 8)}`;
}

export default function ThreadRail({ currentThreadId, onNewThread }: Props) {
	const { data, isLoading, isError } = useListThreadsQuery();

	return (
		<aside aria-label="Recent threads" style={wrapperStyle}>
			<button
				type="button"
				style={newButtonStyle}
				onClick={onNewThread}
				data-testid="new-thread-button"
			>
				+ New thread
			</button>
			<div style={headingStyle}>Recent</div>
			{isLoading ? (
				<div style={emptyStyle}>Loading…</div>
			) : isError ? (
				<div style={emptyStyle}>Couldn’t load threads.</div>
			) : data && data.threads.length > 0 ? (
				data.threads.map((t) => (
					<Link
						key={t.thread_id}
						to={`/intelligence/${t.thread_id}`}
						style={rowStyle(t.thread_id === currentThreadId)}
						aria-current={t.thread_id === currentThreadId ? "page" : undefined}
					>
						{formatTitle(t.thread_id, t.title)}
					</Link>
				))
			) : (
				<div style={emptyStyle}>No threads yet.</div>
			)}
		</aside>
	);
}
