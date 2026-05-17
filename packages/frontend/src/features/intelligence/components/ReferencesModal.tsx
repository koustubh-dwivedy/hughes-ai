/** Modal lifting auditing material (rows + mfQuery + thinking trace,
 * plus the HUG-224 research audit panel when applicable) out of the
 * answer bubble. Closes on overlay click, ESC, or close button. */
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import JsonBlock from "../../../ui/primitives/JsonBlock/JsonBlock";
import type { ThreadTraceEntry } from "../api";
import ResearchAuditPanel from "../research/ResearchAuditPanel";
import ReferencesTrace from "./ReferencesTrace";

interface Props {
	open: boolean;
	onClose: () => void;
	rows: Record<string, unknown>[] | null;
	mfQuery: Record<string, unknown> | null;
	thinkingTrace: ThreadTraceEntry[] | null;
	// HUG-224: both set → render audit panel below chat refs.
	researchPlanId?: string;
	researchThreadId?: string;
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
	overflow: "hidden",
	display: "flex",
	flexDirection: "column",
	boxShadow: "0 24px 60px rgba(15, 23, 42, 0.25)",
};

const headerStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	justifyContent: "space-between",
	background: colors.white,
	padding: `${spacing[5]} ${spacing[6]}`,
	borderBottom: `1px solid ${colors.slate[200]}`,
	flexShrink: 0,
};

const bodyStyle: React.CSSProperties = {
	overflow: "auto",
	padding: spacing[6],
	display: "flex",
	flexDirection: "column",
	gap: spacing[4],
	flex: 1,
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

export default function ReferencesModal({
	open,
	onClose,
	rows,
	mfQuery,
	thinkingTrace,
	researchPlanId,
	researchThreadId,
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
				<header style={headerStyle} data-testid="references-modal-header">
					<h2 style={titleStyle}>References</h2>
					<button
						type="button"
						aria-label="Close references"
						onClick={onClose}
						style={closeButtonStyle}
						data-testid="references-modal-close"
					>
						×
					</button>
				</header>
				<div style={bodyStyle} data-testid="references-modal-body">
					{thinkingTrace && thinkingTrace.length > 0 ? (
						<section data-testid="trace-section">
							<div style={sectionLabelStyle}>
								Thinking trace ({thinkingTrace.length})
							</div>
							<ReferencesTrace entries={thinkingTrace} />
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
					{researchPlanId && researchThreadId ? (
						<ResearchAuditPanel
							threadId={researchThreadId}
							planId={researchPlanId}
						/>
					) : null}
				</div>
			</dialog>
		</div>
	);
	return createPortal(node, document.body);
}
