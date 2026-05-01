import { radii, spacing, typography } from "../../theme/tokens";

interface BannerProps {
	message: string;
	variant?: "info" | "warning";
}

export default function Banner({ message, variant = "info" }: BannerProps) {
	const bg = variant === "warning" ? "#fef9c3" : "#eff6ff";
	const border = variant === "warning" ? "#fde047" : "#bfdbfe";
	const color = variant === "warning" ? "#854d0e" : "#1e40af";
	return (
		<div
			role="note"
			style={{
				backgroundColor: bg,
				border: `1px solid ${border}`,
				borderRadius: radii.lg,
				color,
				fontSize: typography.size.sm,
				fontWeight: typography.weight.medium,
				padding: `${spacing[2]} ${spacing[4]}`,
				marginBottom: spacing[4],
			}}
		>
			{message}
		</div>
	);
}
