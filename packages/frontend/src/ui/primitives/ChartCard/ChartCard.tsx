import { useEffect, useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import { motionDurations, usePrefersReducedMotion } from "../motion";
import type { ChartCardProps } from "./types";

const cardStyle = {
	borderRadius: radii.xl,
	border: `1px solid ${colors.slate[200]}`,
	backgroundColor: colors.white,
	overflow: "hidden" as const,
};

const headerStyle = {
	display: "flex",
	alignItems: "flex-start",
	justifyContent: "space-between",
	padding: `${spacing[4]} ${spacing[6]}`,
	borderBottom: `1px solid ${colors.slate[100]}`,
};

const bodyStyle = {
	padding: `${spacing[4]} ${spacing[6]}`,
	overflowX: "auto" as const,
};

const footerStyle = {
	padding: `${spacing[3]} ${spacing[6]}`,
	borderTop: `1px solid ${colors.slate[100]}`,
	fontSize: typography.size.xs,
	color: colors.slate[500],
};

export default function ChartCard({
	title,
	subtitle,
	actions,
	footer,
	children,
	loading = false,
}: ChartCardProps) {
	const reducedMotion = usePrefersReducedMotion();
	const [opacity, setOpacity] = useState(reducedMotion ? 1 : 0);

	useEffect(() => {
		if (reducedMotion || loading) {
			setOpacity(1);
			return;
		}
		const id = window.setTimeout(() => setOpacity(1), 0);
		return () => window.clearTimeout(id);
	}, [reducedMotion, loading]);

	const entryDuration = reducedMotion ? 0 : motionDurations.chartEntry;

	if (loading) {
		return (
			<output
				aria-label="loading chart"
				style={{
					display: "block",
					borderRadius: radii.xl,
					border: `1px solid ${colors.slate[200]}`,
					backgroundColor: colors.slate[100],
					minHeight: 320,
				}}
			/>
		);
	}

	return (
		<section
			data-chart-card
			style={{
				...cardStyle,
				opacity,
				transition: `opacity ${entryDuration}ms ease`,
			}}
		>
			<div style={headerStyle}>
				<div>
					<h3
						style={{
							margin: 0,
							fontSize: typography.size.sm,
							fontWeight: typography.weight.semibold,
							color: colors.slate[800],
							lineHeight: 1.4,
						}}
					>
						{title}
					</h3>
					{subtitle !== undefined && (
						<p
							style={{
								margin: `${spacing[1]} 0 0`,
								fontSize: typography.size.xs,
								color: colors.slate[500],
								lineHeight: 1.4,
							}}
						>
							{subtitle}
						</p>
					)}
				</div>
				{actions !== undefined && (
					<div style={{ flexShrink: 0, marginLeft: spacing[4] }}>{actions}</div>
				)}
			</div>
			{/* biome-ignore lint/a11y/noNoninteractiveTabindex: scrollable region (overflowX: auto) needs a focusable handle so keyboard users can pan wide chart/table content (axe scrollable-region-focusable) */}
			<div tabIndex={0} style={bodyStyle}>
				{children}
			</div>
			{footer !== undefined && <div style={footerStyle}>{footer}</div>}
		</section>
	);
}
