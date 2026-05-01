import { colors, spacing, typography } from "../../../theme/tokens";
import type { PageHeaderProps } from "./types";

const HEADING_ID = "page-header-title";

export default function PageHeader({
	eyebrow,
	title,
	subtitle,
	actions,
	dateBadge,
}: PageHeaderProps) {
	return (
		<header
			aria-labelledby={HEADING_ID}
			style={{
				display: "flex",
				flexDirection: "row",
				alignItems: "flex-start",
				justifyContent: "space-between",
				borderBottom: `1px solid ${colors.slate[200]}`,
				paddingBottom: spacing[4],
				marginBottom: spacing[6],
			}}
		>
			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[1] }}
			>
				{eyebrow && (
					<span
						style={{
							fontSize: typography.size.xs,
							fontWeight: typography.weight.medium,
							color: colors.indigo[600],
							textTransform: "uppercase",
							letterSpacing: "0.05em",
						}}
					>
						{eyebrow}
					</span>
				)}
				<h1
					id={HEADING_ID}
					style={{
						fontSize: typography.size["2xl"],
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
						margin: 0,
					}}
				>
					{title}
				</h1>
				{subtitle && (
					<p
						style={{
							fontSize: typography.size.sm,
							fontWeight: typography.weight.normal,
							color: colors.slate[500],
							margin: 0,
						}}
					>
						{subtitle}
					</p>
				)}
			</div>
			<div
				style={{
					display: "flex",
					flexDirection: "row",
					alignItems: "center",
					gap: spacing[2],
					flexShrink: 0,
				}}
			>
				{dateBadge}
				{actions}
			</div>
		</header>
	);
}
