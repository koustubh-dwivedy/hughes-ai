import { colors, spacing, typography } from "../../theme/tokens";
import Tooltip from "../../ui/primitives/Tooltip";
import { metricDef } from "../insights/glossary";

interface MetricLabelProps {
	id: string;
	overrideShort?: string;
	color?: string;
	size?: "xs" | "sm";
}

export default function MetricLabel({
	id,
	overrideShort,
	color = colors.slate[600],
	size = "xs",
}: MetricLabelProps) {
	const def = metricDef(id);
	const text = overrideShort ?? def?.short ?? id;
	const tooltip = def?.tooltip;

	const content = (
		<span
			style={{
				display: "inline-flex",
				alignItems: "center",
				gap: spacing[1],
				fontSize: typography.size[size],
				color,
				fontWeight: typography.weight.medium,
				letterSpacing: 0,
			}}
		>
			{text}
			{tooltip && (
				<span
					aria-hidden="true"
					style={{
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						width: 14,
						height: 14,
						borderRadius: "50%",
						border: `1px solid ${colors.slate[300]}`,
						color: colors.slate[400],
						fontSize: 10,
						fontWeight: typography.weight.semibold,
						cursor: "help",
					}}
				>
					i
				</span>
			)}
		</span>
	);

	if (!tooltip) return content;

	return (
		<Tooltip label={tooltip} multiline w={280} withArrow position="top">
			{content}
		</Tooltip>
	);
}
