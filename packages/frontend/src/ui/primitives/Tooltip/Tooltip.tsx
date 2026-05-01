import { Tooltip as MantineTooltip } from "@mantine/core";
import type { TooltipProps } from "@mantine/core";

// Default: position="top", withArrow=true
export default function Tooltip({
	position = "top",
	withArrow = true,
	...props
}: TooltipProps) {
	return (
		<MantineTooltip position={position} withArrow={withArrow} {...props} />
	);
}
