import type { useSearchParams } from "react-router-dom";
import { emit } from "../../shared/telemetry/client";
import { colors, spacing, typography } from "../../theme/tokens";

const BRANCH_OPTIONS = [
	{ value: "", label: "All Branches" },
	{ value: "1", label: "Main Branch" },
	{ value: "2", label: "East Branch" },
	{ value: "3", label: "West Branch" },
];

const OFFICER_OPTIONS = [
	{ value: "", label: "All Officers" },
	{ value: "off-01", label: "Officer #01" },
	{ value: "off-02", label: "Officer #02" },
	{ value: "off-03", label: "Officer #03" },
];

const labelStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	color: colors.slate[600],
	display: "block",
	marginBottom: spacing[1],
};

type SetParams = ReturnType<typeof useSearchParams>[1];

function applyFilterChange(value: string, key: string, set: SetParams) {
	set((prev) => {
		if (value) prev.set(key, value);
		else prev.delete(key);
		return prev;
	});
	emit({ type: "filter.changed", filter_name: key, value });
}

interface FiltersRowProps {
	branchId: string;
	officerId: string;
	setSearchParams: SetParams;
}

export default function FiltersRow({
	branchId,
	officerId,
	setSearchParams,
}: FiltersRowProps) {
	function onBranch(e: React.ChangeEvent<HTMLSelectElement>) {
		applyFilterChange(e.target.value, "branch_id", setSearchParams);
	}
	function onOfficer(e: React.ChangeEvent<HTMLSelectElement>) {
		applyFilterChange(e.target.value, "officer_id", setSearchParams);
	}
	return (
		<div style={{ display: "flex", gap: spacing[4], marginBottom: spacing[6] }}>
			<label>
				<span style={labelStyle}>Branch</span>
				<select aria-label="Branch filter" value={branchId} onChange={onBranch}>
					{BRANCH_OPTIONS.map((o) => (
						<option key={o.value} value={o.value}>
							{o.label}
						</option>
					))}
				</select>
			</label>
			<label>
				<span style={labelStyle}>Officer</span>
				<select
					aria-label="Officer filter"
					value={officerId}
					onChange={onOfficer}
				>
					{OFFICER_OPTIONS.map((o) => (
						<option key={o.value} value={o.value}>
							{o.label}
						</option>
					))}
				</select>
			</label>
		</div>
	);
}
