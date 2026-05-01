import { spacing, typography } from "../../../theme/tokens";

export type TagVariant = "default" | "success" | "warning" | "danger" | "info";
export type TagSize = "sm" | "md";

export interface TagProps {
	label: string;
	variant?: TagVariant;
	size?: TagSize;
	onRemove?: () => void;
}

interface VariantStyle {
	backgroundColor: string;
	color: string;
	border: string;
}

const variantMap: Record<TagVariant, VariantStyle> = {
	default: {
		backgroundColor: "#f1f5f9",
		color: "#334155",
		border: "1px solid #e2e8f0",
	},
	success: {
		backgroundColor: "#f0fdf4",
		color: "#16a34a",
		border: "1px solid #bbf7d0",
	},
	warning: {
		backgroundColor: "#fffbeb",
		color: "#b45309",
		border: "1px solid #fde68a",
	},
	danger: {
		backgroundColor: "#fff1f2",
		color: "#e11d48",
		border: "1px solid #fecdd3",
	},
	info: {
		backgroundColor: "#f0f9ff",
		color: "#0369a1",
		border: "1px solid #bae6fd",
	},
};

export default function Tag({
	label,
	variant = "default",
	size = "sm",
	onRemove,
}: TagProps) {
	const { backgroundColor, color, border } = variantMap[variant];

	const fontSize = size === "sm" ? typography.size.xs : typography.size.sm;
	const padding =
		size === "sm" ? `0 ${spacing[2]}` : `${spacing[1]} ${spacing[3]}`;

	return (
		<span
			style={{
				display: "inline-flex",
				alignItems: "center",
				gap: spacing[1],
				backgroundColor,
				color,
				border,
				borderRadius: "9999px",
				fontSize,
				fontWeight: typography.weight.medium,
				padding,
				lineHeight: "1.5rem",
				whiteSpace: "nowrap",
			}}
		>
			{label}
			{onRemove !== undefined && (
				<button
					type="button"
					onClick={onRemove}
					aria-label={`Remove ${label}`}
					style={{
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						background: "none",
						border: "none",
						cursor: "pointer",
						color: "inherit",
						padding: 0,
						lineHeight: 1,
						fontSize: "inherit",
					}}
				>
					&#215;
				</button>
			)}
		</span>
	);
}
