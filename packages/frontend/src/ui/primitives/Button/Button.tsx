import { Button as MantineButton } from "@mantine/core";
import type { ButtonProps } from "@mantine/core";
import type { ComponentPropsWithoutRef } from "react";

type HughesButtonProps = ButtonProps & ComponentPropsWithoutRef<"button">;

export default function Button({
	variant = "filled",
	color = "indigo",
	...props
}: HughesButtonProps) {
	return <MantineButton variant={variant} color={color} {...props} />;
}
