import type { TooltipProps } from "recharts";
import { colors, radii, spacing, typography } from "../../theme/tokens";

interface ChartTooltipProps extends TooltipProps<number | string, string> {
	formatValue?: (value: number | string, name: string) => string;
}

export function ChartTooltip({
	active,
	payload,
	label,
	formatValue,
}: ChartTooltipProps) {
	if (!active || !payload || payload.length === 0) return null;

	return (
		<div
			style={{
				background: colors.white,
				border: `1px solid ${colors.slate[200]}`,
				borderRadius: radii.md,
				padding: `${spacing[2]} ${spacing[3]}`,
				boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
				fontFamily: typography.fontFamily,
			}}
		>
			{label !== undefined && label !== "" && (
				<p
					style={{
						margin: `0 0 ${spacing[1]} 0`,
						fontSize: typography.size.xs,
						fontWeight: typography.weight.medium,
						color: colors.slate[500],
					}}
				>
					{String(label)}
				</p>
			)}
			{payload.map((entry, i) => (
				<div
					key={entry.name ?? entry.dataKey ?? String(i)}
					style={{
						display: "flex",
						alignItems: "center",
						gap: spacing[2],
						fontSize: typography.size.sm,
					}}
				>
					{entry.color !== undefined && (
						<span
							style={{
								width: 8,
								height: 8,
								borderRadius: "50%",
								backgroundColor: entry.color,
								flexShrink: 0,
								display: "inline-block",
							}}
						/>
					)}
					<span style={{ color: colors.slate[600] }}>{entry.name}:</span>
					<span
						style={{
							color: colors.slate[900],
							fontWeight: typography.weight.semibold,
						}}
					>
						{formatValue
							? formatValue(entry.value ?? 0, entry.name ?? "")
							: String(entry.value ?? "")}
					</span>
				</div>
			))}
		</div>
	);
}
