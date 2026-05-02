import { spacing } from "../../../theme/tokens";

interface Props {
	children: React.ReactNode;
	minWidth?: number;
}

/**
 * Fluid KPI tile grid: auto-fit minmax(minWidth, 1fr). Tiles wrap to
 * however many columns fit at the current viewport — at 1440px users
 * see 4-5 across, at 768px tablet 2-3, at 375px phone exactly 1.
 */
export default function KpiGrid({ children, minWidth = 220 }: Props) {
	return (
		<div
			data-kpi-grid
			style={{
				display: "grid",
				gridTemplateColumns: `repeat(auto-fit, minmax(${minWidth}px, 1fr))`,
				gap: spacing[4],
				marginBottom: spacing[6],
				width: "100%",
			}}
		>
			{children}
		</div>
	);
}
