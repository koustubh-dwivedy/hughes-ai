import { useMemo, useState } from "react";
import type { HistorySummary } from "../../shared/api/api";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import { useGetHistoryListQuery } from "./api";

interface Props {
	onSelect: (id: string) => void;
}

interface DayGroup {
	dateKey: string;
	label: string;
	items: HistorySummary[];
}

function dateKeyOf(iso: string): string {
	return iso.slice(0, 10);
}

export function dayLabel(dateKey: string, today = new Date()): string {
	const todayKey = today.toISOString().slice(0, 10);
	if (dateKey === todayKey) return "Today";
	const yesterday = new Date(today);
	yesterday.setDate(today.getDate() - 1);
	if (dateKey === yesterday.toISOString().slice(0, 10)) return "Yesterday";
	const d = new Date(`${dateKey}T00:00:00`);
	return d.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
		year: d.getFullYear() === today.getFullYear() ? undefined : "numeric",
	});
}

export function groupByDay(items: HistorySummary[]): DayGroup[] {
	const map = new Map<string, HistorySummary[]>();
	for (const item of items) {
		const k = dateKeyOf(item.created_at);
		const list = map.get(k) ?? [];
		list.push(item);
		map.set(k, list);
	}
	const sortedKeys = Array.from(map.keys()).sort((a, b) => (a < b ? 1 : -1));
	return sortedKeys.map((k) => ({
		dateKey: k,
		label: dayLabel(k),
		items: (map.get(k) ?? []).sort((a, b) =>
			a.created_at < b.created_at ? 1 : -1,
		),
	}));
}

const wrapperStyle: React.CSSProperties = {
	padding: `${spacing[3]} ${spacing[2]}`,
	borderTop: `1px solid ${colors.slate[700]}`,
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
	overflow: "hidden",
};

const headingStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[400],
	textTransform: "uppercase",
	letterSpacing: "0.06em",
	margin: 0,
	padding: `0 ${spacing[2]}`,
};

const searchStyle: React.CSSProperties = {
	background: colors.slate[700],
	color: colors.white,
	border: `1px solid ${colors.slate[600]}`,
	borderRadius: radii.sm,
	padding: `${spacing[1]} ${spacing[2]}`,
	fontSize: typography.size.xs,
	fontFamily: typography.fontFamily,
	outline: "none",
};

const listStyle: React.CSSProperties = {
	listStyle: "none",
	margin: 0,
	padding: 0,
	overflowY: "auto",
	maxHeight: 320,
	display: "flex",
	flexDirection: "column",
	gap: spacing[1],
};

const dayHeaderStyle: React.CSSProperties = {
	position: "sticky" as const,
	top: 0,
	background: colors.slate[800],
	padding: `${spacing[1]} ${spacing[2]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	color: colors.slate[400],
	textTransform: "uppercase",
	letterSpacing: "0.04em",
	zIndex: 1,
};

const itemBtnStyle: React.CSSProperties = {
	background: "none",
	border: "none",
	color: colors.slate[300],
	textAlign: "left",
	padding: `${spacing[1]} ${spacing[2]}`,
	fontSize: typography.size.xs,
	cursor: "pointer",
	fontFamily: typography.fontFamily,
	width: "100%",
	overflow: "hidden",
	textOverflow: "ellipsis",
	whiteSpace: "nowrap" as const,
	borderRadius: radii.sm,
};

const emptyStyle: React.CSSProperties = {
	color: colors.slate[500],
	fontSize: typography.size.xs,
	padding: `${spacing[2]} ${spacing[2]}`,
	margin: 0,
};

export default function HistoryRail({ onSelect }: Props) {
	const { data } = useGetHistoryListQuery({ kind: "ask" });
	const items = useMemo<HistorySummary[]>(() => data ?? [], [data]);
	const [query, setQuery] = useState("");

	const filtered = useMemo(() => {
		const q = query.trim().toLowerCase();
		if (q === "") return items;
		return items.filter((i) => i.question.toLowerCase().includes(q));
	}, [items, query]);

	const groups = useMemo(() => groupByDay(filtered), [filtered]);

	return (
		<aside aria-label="Conversation history" style={wrapperStyle}>
			<h2 style={headingStyle}>History</h2>
			<input
				type="search"
				aria-label="Search history"
				placeholder="Search…"
				value={query}
				onChange={(e) => setQuery(e.target.value)}
				style={searchStyle}
			/>
			{groups.length === 0 ? (
				<p style={emptyStyle}>
					{items.length === 0 ? "No history yet." : "No matches."}
				</p>
			) : (
				// biome-ignore lint/a11y/noNoninteractiveTabindex: scrollable region needs a focusable handle so keyboard users can pan the list (axe scrollable-region-focusable)
				<ul tabIndex={0} style={listStyle}>
					{groups.map((group) => (
						<li key={group.dateKey}>
							<h3 style={dayHeaderStyle}>{group.label}</h3>
							<ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
								{group.items.map((item) => (
									<li key={item.id}>
										<button
											type="button"
											onClick={() => onSelect(item.id)}
											style={itemBtnStyle}
											title={item.question}
										>
											{item.question}
										</button>
									</li>
								))}
							</ul>
						</li>
					))}
				</ul>
			)}
		</aside>
	);
}
