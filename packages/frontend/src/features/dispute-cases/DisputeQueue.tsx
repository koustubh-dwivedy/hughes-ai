import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import PageHeader from "../../ui/primitives/PageHeader";
import Tag from "../../ui/primitives/Tag";
import KpiStrip from "./KpiStrip";
import { getOverride, useCaseProgressVersion } from "./data/caseProgressStore";
import { formatDate, slaLabel, slaVariant } from "./format";
import { DISPUTE_CASES } from "./mockData";
import type { DisputeCase, DisputeType } from "./types";

type Filter = "All" | DisputeType;
const FILTERS: Filter[] = ["All", "VOD", "FRAUD"];

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
		<div style={{ display: "flex", gap: spacing[2] }}>
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
						{f === "FRAUD" ? "Fraud" : f}
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
					label={c.type === "FRAUD" ? "Fraud" : "VOD"}
					variant={c.type === "FRAUD" ? "danger" : "default"}
				/>
			</td>
			<td style={tdStyle}>{c.ccc ?? "—"}</td>
			<td style={tdStyle}>{c.acdvNumber ?? "—"}</td>
			<td style={tdStyle}>{c.channel}</td>
			<td style={tdStyle}>{formatDate(c.receivedDate)}</td>
			<td style={tdStyle}>
				<Tag
					label={slaLabel(c.slaDueDate)}
					variant={slaVariant(c.slaDueDate)}
				/>
			</td>
			<td style={tdStyle}>
				<Tag label={effectiveStatus} variant={statusVariant(effectiveStatus)} />
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
		(c) => filter === "All" || c.type === filter,
	);

	return (
		<div>
			<PageHeader
				eyebrow="Dispute Center"
				title="Case Queue"
				subtitle="Credit-bureau disputes — validation-of-debt and identity-theft cases, sorted by SLA urgency."
				actions={<FilterTabs value={filter} onChange={setFilter} />}
			/>
			<KpiStrip cases={DISPUTE_CASES} />
			<div
				style={{
					border: `1px solid ${colors.slate[200]}`,
					borderRadius: radii.xl,
					overflow: "hidden",
					backgroundColor: colors.white,
				}}
			>
				<table style={{ width: "100%", borderCollapse: "collapse" }}>
					<thead>
						<tr>
							<th style={thStyle}>Case</th>
							<th style={thStyle}>Type</th>
							<th style={thStyle}>CCC</th>
							<th style={thStyle}>ACDV #</th>
							<th style={thStyle}>Channel</th>
							<th style={thStyle}>Received</th>
							<th style={thStyle}>SLA</th>
							<th style={thStyle}>Status</th>
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
