import type { Meta, StoryObj } from "@storybook/react";
import Tooltip from "./Tooltip";

const meta: Meta<typeof Tooltip> = {
	component: Tooltip,
	title: "Primitives/Tooltip",
	parameters: { layout: "centered" },
};
export default meta;

type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
	render: () => (
		<Tooltip label="This metric is calculated monthly">
			<button type="button">Hover for info</button>
		</Tooltip>
	),
};

export const NoArrow: Story = {
	render: () => (
		<Tooltip label="No arrow tooltip" withArrow={false}>
			<button type="button">Hover me</button>
		</Tooltip>
	),
};

export const BottomPosition: Story = {
	render: () => (
		<Tooltip label="Appears below" position="bottom">
			<button type="button">Hover me</button>
		</Tooltip>
	),
};

export const LongContent: Story = {
	render: () => (
		<Tooltip
			label="This is a longer tooltip explanation that provides more context about the metric being shown to the user."
			multiline
			w={240}
		>
			<button type="button">Hover for long tip</button>
		</Tooltip>
	),
};
