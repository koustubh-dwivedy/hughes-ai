import { colors, radii, spacing, typography } from "../../theme/tokens";

export type InsightTone = "info" | "warn" | "success" | "neutral";

interface InsightCardProps {
	bullets: string[];
	tone?: InsightTone;
	title?: string;
}

const TONE_BG: Record<InsightTone, string> = {
	info: "#eff6ff",
	warn: "#fffbeb",
	success: "#f0fdf4",
	neutral: colors.slate[50],
};

const TONE_BORDER: Record<InsightTone, string> = {
	info: "#3b82f6",
	warn: "#d97706",
	success: "#16a34a",
	neutral: colors.slate[400],
};

const TONE_ICON: Record<InsightTone, string> = {
	info: "💡",
	warn: "⚠️",
	success: "✓",
	neutral: "•",
};

export default function InsightCard({
	bullets,
	tone = "info",
	title,
}: InsightCardProps) {
	if (bullets.length === 0) return null;
	return (
		<aside
			aria-label="Insight"
			style={{
				display: "flex",
				gap: spacing[3],
				padding: `${spacing[3]} ${spacing[4]}`,
				backgroundColor: TONE_BG[tone],
				borderLeft: `3px solid ${TONE_BORDER[tone]}`,
				borderRadius: radii.sm,
			}}
		>
			<span aria-hidden="true" style={{ fontSize: typography.size.base }}>
				{TONE_ICON[tone]}
			</span>
			<div style={{ flex: 1 }}>
				{title && (
					<p
						style={{
							margin: 0,
							marginBottom: spacing[1],
							fontSize: typography.size.xs,
							fontWeight: typography.weight.semibold,
							color: colors.slate[700],
							textTransform: "uppercase",
							letterSpacing: "0.05em",
						}}
					>
						{title}
					</p>
				)}
				<ul
					style={{
						margin: 0,
						paddingLeft: spacing[4],
						color: colors.slate[700],
						fontSize: typography.size.sm,
						lineHeight: 1.5,
					}}
				>
					{bullets.map((b) => (
						<li key={b}>{b}</li>
					))}
				</ul>
			</div>
		</aside>
	);
}
