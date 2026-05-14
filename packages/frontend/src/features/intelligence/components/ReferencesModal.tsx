/**
 * Centered modal that lifts auditing material (source rows + the
 * MetricFlow query) out of the main answer bubble.
 *
 * Triggered by a "References" pill in the answer; backdrop blurs the
 * conversation behind it. Closes on overlay click, ESC, or the close
 * button. Renders portaled to <body> so it's not constrained by the
 * conversation panel's overflow:auto.
 */

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import JsonBlock from "../../../ui/primitives/JsonBlock/JsonBlock";
import type { ThreadTraceEntry } from "../api";

interface Props {
	open: boolean;
	onClose: () => void;
	rows: Record<string, unknown>[] | null;
	mfQuery: Record<string, unknown> | null;
	thinkingTrace: ThreadTraceEntry[] | null;
}

const overlayStyle: React.CSSProperties = {
	position: "fixed",
	inset: 0,
	background: "rgba(15, 23, 42, 0.55)",
	backdropFilter: "blur(6px)",
	WebkitBackdropFilter: "blur(6px)",
	display: "flex",
	alignItems: "center",
	justifyContent: "center",
	padding: spacing[4],
	zIndex: 1000,
};

const dialogStyle: React.CSSProperties = {
	background: colors.white,
	borderRadius: radii.lg,
	width: "min(880px, 100%)",
	maxHeight: "85vh",
	overflow: "auto",
	padding: spacing[6],
	boxShadow: "0 24px 60px rgba(15, 23, 42, 0.25)",
	display: "flex",
	flexDirection: "column",
	gap: spacing[4],
};

const headerStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	justifyContent: "space-between",
};

const titleStyle: React.CSSProperties = {
	fontSize: typography.size.lg,
	fontWeight: typography.weight.medium,
	color: colors.slate[800],
	margin: 0,
};

const closeButtonStyle: React.CSSProperties = {
	background: "transparent",
	border: "none",
	cursor: "pointer",
	color: colors.slate[600],
	fontSize: typography.size.lg,
	lineHeight: 1,
	padding: spacing[1],
};

const sectionLabelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	color: colors.slate[600],
	textTransform: "uppercase",
	letterSpacing: "0.04em",
	marginBottom: spacing[2],
};

const tableWrapStyle: React.CSSProperties = {
	overflowX: "auto",
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	background: colors.white,
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
					{rows.slice(0, 100).map((r, idx) => (
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

const traceListStyle: React.CSSProperties = {
	listStyle: "none",
	margin: 0,
	padding: spacing[3],
	display: "flex",
	flexDirection: "column",
	gap: spacing[2],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	background: colors.slate[50],
};

const traceItemStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "auto 1fr",
	columnGap: spacing[3],
	rowGap: spacing[1],
	fontSize: typography.size.xs,
};

const traceStepBadgeStyle: React.CSSProperties = {
	background: colors.indigo[700],
	color: colors.white,
	borderRadius: radii.sm,
	padding: `0 ${spacing[2]}`,
	fontWeight: typography.weight.medium,
	alignSelf: "start",
	minWidth: 28,
	textAlign: "center",
};

const traceLabelStyle: React.CSSProperties = {
	color: colors.slate[800],
	fontWeight: typography.weight.medium,
};

const traceMetaStyle: React.CSSProperties = {
	gridColumn: "2 / -1",
	color: colors.slate[500],
	fontSize: typography.size.xs,
};

function _kindIcon(kind: string): string {
	switch (kind) {
		case "tool_call":
			return "→";
		case "tool_result":
			return "←";
		case "thinking_text":
			return "•";
		default:
			return "·";
	}
}

function TraceList({ entries }: { entries: ThreadTraceEntry[] }) {
	return (
		<ol style={traceListStyle}>
			{entries.map((entry) => (
				<li
					key={`${entry.step}-${entry.kind}-${entry.at}`}
					style={traceItemStyle}
				>
					<span style={traceStepBadgeStyle} aria-label={`step ${entry.step}`}>
						{entry.step}
					</span>
					<span style={traceLabelStyle}>
						{_kindIcon(entry.kind)} {entry.label}
					</span>
					<span style={traceMetaStyle}>
						{entry.kind}
						{entry.tool ? ` · ${entry.tool}` : ""}
					</span>
				</li>
			))}
		</ol>
	);
}

export default function ReferencesModal({
	open,
	onClose,
	rows,
	mfQuery,
	thinkingTrace,
}: Props) {
	useEffect(() => {
		if (!open) return;
		function onKey(e: KeyboardEvent): void {
			if (e.key === "Escape") onClose();
		}
		document.addEventListener("keydown", onKey);
		return () => document.removeEventListener("keydown", onKey);
	}, [open, onClose]);

	if (!open) return null;
	if (typeof document === "undefined") return null;

	const node = (
		<div
			role="presentation"
			style={overlayStyle}
			onClick={onClose}
			onKeyDown={(e) => {
				if (e.key === "Escape") onClose();
			}}
		>
			<dialog
				open
				aria-label="Answer references"
				style={dialogStyle}
				onClick={(e) => e.stopPropagation()}
				onKeyDown={(e) => e.stopPropagation()}
			>
				<header style={headerStyle}>
					<h2 style={titleStyle}>References</h2>
					<button
						type="button"
						aria-label="Close references"
						onClick={onClose}
						style={closeButtonStyle}
					>
						×
					</button>
				</header>
				{thinkingTrace && thinkingTrace.length > 0 ? (
					<section data-testid="trace-section">
						<div style={sectionLabelStyle}>
							Thinking trace ({thinkingTrace.length})
						</div>
						<TraceList entries={thinkingTrace} />
					</section>
				) : null}
				{rows && rows.length > 0 ? (
					<section>
						<div style={sectionLabelStyle}>Source rows ({rows.length})</div>
						<RowsTable rows={rows} />
					</section>
				) : null}
				{mfQuery ? (
					<section>
						<div style={sectionLabelStyle}>MetricFlow query</div>
						<JsonBlock value={mfQuery} label="MetricFlow query" />
					</section>
				) : null}
			</dialog>
		</div>
	);
	return createPortal(node, document.body);
}
