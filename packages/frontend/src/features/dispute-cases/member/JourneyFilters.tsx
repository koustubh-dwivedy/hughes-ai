import { Search } from "lucide-react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Input from "../../../ui/primitives/Input";
import type { CategoryFilter, JourneyFilterState } from "./journeyFilter";

interface Props {
	state: JourneyFilterState;
	onChange: (next: JourneyFilterState) => void;
	count: number;
	total: number;
}

const CATEGORIES: { key: CategoryFilter; label: string }[] = [
	{ key: "all", label: "All" },
	{ key: "complaint", label: "Complaints" },
	{ key: "contact", label: "Contacts" },
	{ key: "money", label: "Money" },
	{ key: "lifecycle", label: "Lifecycle" },
];

const dateInputStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[800],
	padding: `${spacing[1]} ${spacing[2]}`,
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.md,
	backgroundColor: colors.white,
	fontFamily: typography.fontFamily,
};

function Chip({
	label,
	active,
	onClick,
}: { label: string; active: boolean; onClick: () => void }) {
	return (
		<button
			type="button"
			onClick={onClick}
			aria-pressed={active}
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
			{label}
		</button>
	);
}

function DateRange({ state, onChange }: Pick<Props, "state" | "onChange">) {
	const labelStyle: React.CSSProperties = {
		fontSize: typography.size.xs,
		color: colors.slate[500],
		display: "inline-flex",
		alignItems: "center",
		gap: spacing[1],
	};
	return (
		<div style={{ display: "flex", gap: spacing[2], alignItems: "center" }}>
			<label style={labelStyle}>
				From
				<input
					type="date"
					aria-label="From date"
					value={state.start ?? ""}
					onChange={(e) =>
						onChange({ ...state, start: e.target.value || undefined })
					}
					style={dateInputStyle}
				/>
			</label>
			<label style={labelStyle}>
				To
				<input
					type="date"
					aria-label="To date"
					value={state.end ?? ""}
					onChange={(e) =>
						onChange({ ...state, end: e.target.value || undefined })
					}
					style={dateInputStyle}
				/>
			</label>
			{(state.start || state.end) && (
				<button
					type="button"
					onClick={() =>
						onChange({ ...state, start: undefined, end: undefined })
					}
					style={{
						background: "none",
						border: "none",
						color: colors.slate[600],
						cursor: "pointer",
						fontSize: typography.size.sm,
						textDecoration: "underline",
					}}
				>
					Clear
				</button>
			)}
		</div>
	);
}

export default function JourneyFilters({
	state,
	onChange,
	count,
	total,
}: Props) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[3] }}>
			<div
				style={{
					display: "flex",
					gap: spacing[3],
					alignItems: "center",
					flexWrap: "wrap",
				}}
			>
				<div style={{ flex: "1 1 240px", minWidth: 200 }}>
					<Input
						value={state.query}
						onChange={(e) =>
							onChange({ ...state, query: e.currentTarget.value })
						}
						placeholder="Search touchpoints…"
						aria-label="Search touchpoints"
						leftSection={<Search size={16} />}
					/>
				</div>
				<DateRange state={state} onChange={onChange} />
			</div>
			<div
				style={{
					display: "flex",
					gap: spacing[2],
					alignItems: "center",
					flexWrap: "wrap",
				}}
			>
				{CATEGORIES.map((cat) => (
					<Chip
						key={cat.key}
						label={cat.label}
						active={state.category === cat.key}
						onClick={() => onChange({ ...state, category: cat.key })}
					/>
				))}
				<span
					style={{
						marginLeft: "auto",
						fontSize: typography.size.xs,
						color: colors.slate[500],
					}}
				>
					{count} of {total} touchpoints
				</span>
			</div>
		</div>
	);
}
