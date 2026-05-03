import type { Headline } from "../insights/headlines";
import { colors, radii, spacing, typography } from "../../theme/tokens";

const TONE_BG: Record<Headline["tone"], string> = {
	success: colors.slate[50],
	warn: colors.slate[50],
	info: colors.slate[50],
	neutral: colors.slate[50],
};

const TONE_BORDER: Record<Headline["tone"], string> = {
	success: colors.slate[200],
	warn: colors.slate[300],
	info: colors.slate[200],
	neutral: colors.slate[200],
};

const CALLOUT_TONE_COLOR: Record<
	"success" | "warn" | "info",
	{ bg: string; fg: string; icon: string }
> = {
	success: { bg: "#dcfce7", fg: "#15803d", icon: "✓" },
	warn: { bg: "#fef3c7", fg: "#b45309", icon: "⚠" },
	info: { bg: colors.slate[100], fg: colors.slate[800], icon: "ℹ" },
};

interface DashboardHeadlineProps {
	headline: Headline;
}

export default function DashboardHeadline({ headline }: DashboardHeadlineProps) {
	return (
		<section
			aria-label="Dashboard headline"
			style={{
				background: TONE_BG[headline.tone],
				border: `1px solid ${TONE_BORDER[headline.tone]}`,
				borderRadius: radii.xl,
				padding: spacing[6],
				marginBottom: spacing[6],
			}}
		>
			<p
				style={{
					margin: 0,
					marginBottom: spacing[4],
					fontSize: typography.size.lg,
					lineHeight: 1.45,
					fontWeight: typography.weight.semibold,
					color: colors.slate[900],
				}}
			>
				{headline.lede}
			</p>
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
					gap: spacing[3],
				}}
			>
				{headline.callouts.map((c) => {
					const tone = CALLOUT_TONE_COLOR[c.tone];
					return (
						<div
							key={`${c.label}-${c.body}`}
							style={{
								display: "flex",
								alignItems: "flex-start",
								gap: spacing[3],
								padding: `${spacing[3]} ${spacing[4]}`,
								backgroundColor: colors.white,
								borderRadius: radii.lg,
								border: `1px solid ${colors.slate[100]}`,
							}}
						>
							<span
								aria-hidden="true"
								style={{
									display: "inline-flex",
									alignItems: "center",
									justifyContent: "center",
									width: 24,
									height: 24,
									borderRadius: "50%",
									backgroundColor: tone.bg,
									color: tone.fg,
									fontWeight: typography.weight.bold,
									fontSize: typography.size.sm,
									flexShrink: 0,
								}}
							>
								{tone.icon}
							</span>
							<div style={{ flex: 1, minWidth: 0 }}>
								<p
									style={{
										margin: 0,
										marginBottom: 2,
										fontSize: typography.size.xs,
										fontWeight: typography.weight.semibold,
										color: tone.fg,
										textTransform: "uppercase",
										letterSpacing: "0.05em",
									}}
								>
									{c.label}
								</p>
								<p
									style={{
										margin: 0,
										fontSize: typography.size.sm,
										color: colors.slate[700],
										lineHeight: 1.45,
									}}
								>
									{c.body}
								</p>
							</div>
						</div>
					);
				})}
			</div>
		</section>
	);
}
