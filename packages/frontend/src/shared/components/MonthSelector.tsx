import { useEffect } from "react";
import { useGetAvailableMonthsQuery } from "../../features/data-sources/api";
import { useDashboardContext } from "../context/DashboardContext";
import { colors, radii, spacing, typography } from "../../theme/tokens";

interface MonthSelectorProps {
	surface: "executive" | "deposits" | "past-due" | "officer-branch";
}

function formatMonth(iso: string): string {
	const [y, m] = iso.split("-").map(Number);
	const d = new Date(y, m - 1, 1);
	return new Intl.DateTimeFormat("en-US", {
		month: "short",
		year: "numeric",
	}).format(d);
}

export default function MonthSelector({ surface }: MonthSelectorProps) {
	const { asOfDate, setAsOfDate } = useDashboardContext();
	const { data, isLoading } = useGetAvailableMonthsQuery(surface);
	const months = data?.months ?? [];
	const latest = months[0];

	// If the URL has no asOfDate (or one not in the available list), settle
	// onto the latest month so charts render against valid data on first load.
	useEffect(() => {
		if (months.length === 0) return;
		if (!asOfDate || !months.includes(asOfDate)) {
			setAsOfDate(latest);
		}
	}, [months, asOfDate, latest, setAsOfDate]);

	if (isLoading || months.length === 0) {
		return (
			<output
				aria-label="Loading available months"
				style={{
					display: "inline-flex",
					alignItems: "center",
					fontSize: typography.size.xs,
					color: colors.slate[400],
					padding: `${spacing[1]} ${spacing[3]}`,
					border: `1px dashed ${colors.slate[200]}`,
					borderRadius: radii.md,
					whiteSpace: "nowrap",
				}}
			>
				Loading months…
			</output>
		);
	}

	return (
		<label
			style={{
				display: "inline-flex",
				alignItems: "center",
				gap: spacing[2],
			}}
		>
			<span
				style={{
					fontSize: typography.size.xs,
					color: colors.slate[500],
					textTransform: "uppercase",
					letterSpacing: "0.05em",
					fontWeight: typography.weight.semibold,
				}}
			>
				Month
			</span>
			<select
				aria-label="As-of month"
				value={asOfDate ?? latest}
				onChange={(e) => setAsOfDate(e.target.value)}
				style={{
					fontSize: typography.size.sm,
					color: colors.slate[800],
					padding: `${spacing[1]} ${spacing[3]}`,
					border: `1px solid ${colors.slate[300]}`,
					borderRadius: radii.md,
					backgroundColor: colors.white,
					fontFamily: typography.fontFamily,
					cursor: "pointer",
				}}
			>
				{months.map((m) => (
					<option key={m} value={m}>
						{formatMonth(m)}
					</option>
				))}
			</select>
		</label>
	);
}
