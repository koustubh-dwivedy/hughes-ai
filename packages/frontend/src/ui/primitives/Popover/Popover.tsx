import { Popover as MantinePopover } from "@mantine/core";
import type { PopoverProps } from "@mantine/core";

// Default: withArrow=true, shadow="md"
export default function Popover({
	withArrow = true,
	shadow = "md",
	...props
}: PopoverProps) {
	return <MantinePopover withArrow={withArrow} shadow={shadow} {...props} />;
}

export const PopoverTarget = MantinePopover.Target;
export const PopoverDropdown = MantinePopover.Dropdown;
