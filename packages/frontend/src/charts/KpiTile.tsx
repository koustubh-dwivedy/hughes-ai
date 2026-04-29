import { colors, radii, spacing, typography } from "../theme/tokens";

const POSITIVE_COLOR = "#16a34a";
const NEGATIVE_COLOR = "#dc2626";

type Direction = "up" | "down" | "flat" | null;

function deltaDirection(delta: number | undefined): Direction {
	if (delta === undefined) return null;
	if (delta > 0) return "up";
	if (delta < 0) return "down";
	return "flat";
}

function arrowFor(dir: Direction): string {
	if (dir === "up") return "↑";
	if (dir === "down") return "↓";
	return "—";
}

function colorFor(dir: Direction): string {
	if (dir === "up") return POSITIVE_COLOR;
	if (dir === "down") return NEGATIVE_COLOR;
	return colors.slate[400];
}

interface KpiTileProps {
	label: string;
	value: string | number;
	delta?: number;
	deltaLabel?: string;
	loading?: boolean;
}

/**
 * @example
 * <KpiTile
 *   label="Total Loan Balance"
 *   value="$42.5M"
 *   delta={2.3}
 *   deltaLabel="+$2.3M MoM"
 * />
 */
export default function KpiTile({
	label,
	value,
	delta,
	deltaLabel,
	loading = false,
}: KpiTileProps) {
	if (loading) {
		return (
			<output
				aria-label="loading"
				style={{
					display: "block",
					width: 180,
					height: 90,
					backgroundColor: colors.slate[100],
					borderRadius: radii.lg,
				}}
			>
				Loading…
			</output>
		);
	}

	const dir = deltaDirection(delta);

	return (
		<div
			style={{
				display: "inline-flex",
				flexDirection: "column",
				gap: spacing[1],
				padding: spacing[4],
				border: `1px solid ${colors.slate[200]}`,
				borderRadius: radii.lg,
				backgroundColor: colors.white,
				minWidth: 160,
			}}
		>
			<span
				style={{
					fontSize: typography.size.xs,
					fontWeight: typography.weight.medium,
					color: colors.slate[500],
					textTransform: "uppercase",
					letterSpacing: "0.05em",
				}}
			>
				{label}
			</span>
			<span
				style={{
					fontSize: typography.size["2xl"],
					fontWeight: typography.weight.bold,
					color: colors.slate[900],
					lineHeight: 1.2,
				}}
			>
				{value}
			</span>
			{dir !== null && (
				<span
					style={{
						fontSize: typography.size.xs,
						color: colorFor(dir),
						fontWeight: typography.weight.medium,
					}}
				>
					{arrowFor(dir)} {deltaLabel ?? String(Math.abs(delta ?? 0))}
				</span>
			)}
		</div>
	);
}
