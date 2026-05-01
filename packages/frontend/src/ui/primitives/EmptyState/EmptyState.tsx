import type React from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";

export interface EmptyStateProps {
	icon?: React.ReactNode;
	headline: string;
	body?: string;
	action?: { label: string; onClick: () => void };
}

export default function EmptyState({
	icon,
	headline,
	body,
	action,
}: EmptyStateProps) {
	return (
		<output
			style={{
				display: "flex",
				flexDirection: "column",
				alignItems: "center",
				justifyContent: "center",
				textAlign: "center",
				padding: spacing[8],
				gap: spacing[3],
			}}
		>
			{icon !== undefined && (
				<div
					style={{
						width: "48px",
						height: "48px",
						color: colors.slate[400],
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
					}}
				>
					{icon}
				</div>
			)}

			<p
				style={{
					margin: 0,
					fontSize: typography.size.lg,
					fontWeight: typography.weight.semibold,
					color: colors.slate[700],
				}}
			>
				{headline}
			</p>

			{body !== undefined && (
				<p
					style={{
						margin: 0,
						fontSize: typography.size.sm,
						color: colors.slate[500],
					}}
				>
					{body}
				</p>
			)}

			{action !== undefined && (
				<button
					type="button"
					onClick={action.onClick}
					style={{
						marginTop: spacing[2],
						padding: `${spacing[2]} ${spacing[4]}`,
						backgroundColor: colors.indigo[600],
						color: colors.white,
						border: "none",
						borderRadius: radii.md,
						fontSize: typography.size.sm,
						fontWeight: typography.weight.medium,
						cursor: "pointer",
					}}
				>
					{action.label}
				</button>
			)}
		</output>
	);
}
