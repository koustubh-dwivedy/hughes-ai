import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import PageHeader from "../../ui/primitives/PageHeader";
import Tag from "../../ui/primitives/Tag";
import KpiStrip from "./KpiStrip";
import { getOverride, useCaseProgressVersion } from "./data/caseProgressStore";
import { formatDate, slaLabel, slaVariant } from "./format";
import { DISPUTE_CASES } from "./mockData";
import {
	type DisputeCase,
	type DisputeCategory,
	categoryForReason,
} from "./types";

/** The ACDV reason code a case carries (data-accuracy or fraud detail). */
function reasonCode(c: DisputeCase): string {
	return c.type === "DATA_ACCURACY"
		? c.dataAccuracy.reasonCode
		: c.fraud.reasonCode;
}

/** The dispute category (master-table mapping) shown as the case "Type". */
function caseCategory(c: DisputeCase): DisputeCategory {
	return categoryForReason(reasonCode(c));
}

/** The e-OSCAR response code — recommended while open, furnished once resolved. */
function responseFor(c: DisputeCase): string {
	return c.type === "DATA_ACCURACY"
		? c.dataAccuracy.recommendedResponse
		: c.fraud.recommendedResponse;
}

/** Whether the agent may auto-furnish (data-accuracy, all gates pass) or a human decides. */
function responseMode(c: DisputeCase): "Auto" | "Review" {
	return c.type === "DATA_ACCURACY" &&
		c.dataAccuracy.autonomyMode === "autonomous"
		? "Auto"
		: "Review";
}

type Filter = "All" | DisputeCategory;

/** Canonical category order; filter tabs show only categories present in data. */
const CATEGORY_ORDER: DisputeCategory[] = [
	"Ownership",
	"Closed Account",
	"Account Specific",
	"Account Comments",
	"Account Dates",
	"Account Derogatory Payments",
	"Collection",
	"Bankruptcy",
	"Fraud",
	"Account Not Specific",
];

const PRESENT_CATEGORIES = new Set(DISPUTE_CASES.map(caseCategory));
const FILTERS: Filter[] = [
	"All",
	...CATEGORY_ORDER.filter((c) => PRESENT_CATEGORIES.has(c)),
];

const CATEGORY_VARIANT: Record<
	DisputeCategory,
	"default" | "danger" | "warning" | "info"
> = {
	Ownership: "warning",
	"Closed Account": "info",
	"Account Specific": "info",
	"Account Comments": "info",
	"Account Dates": "info",
	"Account Derogatory Payments": "warning",
	Collection: "warning",
	Bankruptcy: "warning",
	Fraud: "danger",
	"Account Not Specific": "default",
};

const thStyle: React.CSSProperties = {
	textAlign: "left",
	padding: `${spacing[2]} ${spacing[3]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.05em",
	borderBottom: `1px solid ${colors.slate[200]}`,
	whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
	padding: `${spacing[3]} ${spacing[3]}`,
	fontSize: typography.size.sm,
	color: colors.slate[700],
	borderBottom: `1px solid ${colors.slate[100]}`,
	whiteSpace: "nowrap",
};

function statusVariant(status: string) {
	if (status === "Resolved") return "success" as const;
	if (status === "Decide" || status === "Triangulate ID")
		return "warning" as const;
	return "info" as const;
}

function FilterTabs({
	value,
	onChange,
}: { value: Filter; onChange: (f: Filter) => void }) {
	return (
		<div
			style={{
				display: "flex",
				gap: spacing[2],
				flexWrap: "wrap",
				marginBottom: spacing[4],
			}}
		>
			{FILTERS.map((f) => {
				const active = f === value;
				return (
					<button
						key={f}
						type="button"
						onClick={() => onChange(f)}
						style={{
							padding: `${spacing[1]} ${spacing[3]}`,
							borderRadius: radii.md,
							border: `1px solid ${active ? colors.slate[800] : colors.slate[200]}`,
							backgroundColor: active ? colors.slate[800] : colors.white,
							color: active ? colors.white : colors.slate[600],
							fontSize: typography.size.sm,
							fontWeight: typography.weight.medium,
							cursor: "pointer",
						}}
					>
						{f}
					</button>
				);
			})}
		</div>
	);
}

function CaseRow({ c }: { c: DisputeCase }) {
	const navigate = useNavigate();
	const effectiveStatus = getOverride(c.id)?.status ?? c.status;
	return (
		<tr
			tabIndex={0}
			onClick={() => navigate(`/disputes/${c.id}`)}
			onKeyDown={(e) => {
				if (e.key === "Enter") navigate(`/disputes/${c.id}`);
			}}
			style={{ cursor: "pointer" }}
			onMouseEnter={(e) => {
				e.currentTarget.style.backgroundColor = colors.slate[50];
			}}
			onMouseLeave={(e) => {
				e.currentTarget.style.backgroundColor = "transparent";
			}}
		>
			<td style={{ ...tdStyle, fontWeight: typography.weight.medium }}>
				{c.id}
			</td>
			<td style={tdStyle}>
				<Tag
					label={caseCategory(c)}
					variant={CATEGORY_VARIANT[caseCategory(c)]}
				/>
			</td>
			<td style={tdStyle}>{reasonCode(c)}</td>
			<td style={tdStyle}>{c.ccc ?? "—"}</td>
			<td style={tdStyle}>{c.acdvNumber ?? "—"}</td>
			<td style={tdStyle}>{c.channel}</td>
			<td style={tdStyle}>{formatDate(c.receivedDate)}</td>
			<td style={tdStyle}>
				{effectiveStatus === "Resolved" ? (
					<span style={{ color: colors.slate[400] }}>—</span>
				) : (
					<Tag
						label={slaLabel(c.slaDueDate)}
						variant={slaVariant(c.slaDueDate)}
					/>
				)}
			</td>
			<td style={tdStyle}>
				<Tag label={effectiveStatus} variant={statusVariant(effectiveStatus)} />
			</td>
			<td style={tdStyle}>
				<span
					style={{
						display: "inline-flex",
						alignItems: "center",
						gap: spacing[2],
					}}
				>
					<Tag label={responseFor(c)} variant="info" />
					<span
						style={{ fontSize: typography.size.xs, color: colors.slate[500] }}
					>
						{effectiveStatus === "Resolved" ? "furnished" : responseMode(c)}
					</span>
				</span>
			</td>
			<td style={tdStyle}>{c.assignee}</td>
		</tr>
	);
}

export default function DisputeQueue() {
	const [filter, setFilter] = useState<Filter>("All");
	// Subscribe so resolving a case this session re-renders the queue.
	useCaseProgressVersion();
	const rows = DISPUTE_CASES.filter(
		(c) => filter === "All" || caseCategory(c) === filter,
	);

	return (
		<div>
			<PageHeader
				eyebrow="Dispute Center"
				title="Case Queue"
				subtitle="Credit-bureau disputes — ACDV data-accuracy (the automation core) and identity-theft cases, sorted by SLA urgency."
			/>
			<KpiStrip cases={DISPUTE_CASES} />
			<FilterTabs value={filter} onChange={setFilter} />
			<div
				style={{
					border: `1px solid ${colors.slate[200]}`,
					borderRadius: radii.xl,
					overflowX: "auto",
					backgroundColor: colors.white,
				}}
			>
				<table
					style={{
						width: "100%",
						minWidth: "max-content",
						borderCollapse: "collapse",
					}}
				>
					<thead>
						<tr>
							<th style={thStyle}>Case</th>
							<th style={thStyle}>Type</th>
							<th style={thStyle}>Reason</th>
							<th style={thStyle}>CCC</th>
							<th style={thStyle}>ACDV #</th>
							<th style={thStyle}>Channel</th>
							<th style={thStyle}>Received</th>
							<th style={thStyle}>SLA</th>
							<th style={thStyle}>Status</th>
							<th style={thStyle}>Response</th>
							<th style={thStyle}>Assignee</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((c) => (
							<CaseRow key={c.id} c={c} />
						))}
					</tbody>
				</table>
			</div>
		</div>
	);
}
