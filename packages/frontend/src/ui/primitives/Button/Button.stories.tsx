import type { Meta, StoryObj } from "@storybook/react";
import Button from "./Button";

const meta: Meta<typeof Button> = {
	component: Button,
	title: "Primitives/Button",
	parameters: { layout: "centered" },
};
export default meta;

type Story = StoryObj<typeof Button>;

export const Primary: Story = {
	args: {
		children: "Primary Button",
		variant: "filled",
		color: "indigo",
	},
};

export const Secondary: Story = {
	args: {
		children: "Secondary Button",
		variant: "outline",
		color: "indigo",
	},
};

export const Ghost: Story = {
	args: {
		children: "Ghost Button",
		variant: "subtle",
		color: "indigo",
	},
};

export const Disabled: Story = {
	args: {
		children: "Disabled Button",
		disabled: true,
	},
};

export const Loading: Story = {
	args: {
		children: "Loading Button",
		loading: true,
	},
};
