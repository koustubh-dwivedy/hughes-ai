import type { Meta, StoryObj } from "@storybook/react";
import Input from "./Input";

const meta: Meta<typeof Input> = {
	component: Input,
	title: "Primitives/Input",
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof Input>;

export const Default: Story = {
	args: {
		placeholder: "Enter a value...",
	},
};

export const WithLabel: Story = {
	args: {
		label: "Loan Amount",
		placeholder: "0.00",
	},
};

export const WithError: Story = {
	args: {
		label: "Member ID",
		placeholder: "Enter member ID",
		error: "Member ID is required",
	},
};

export const WithDescription: Story = {
	args: {
		label: "Search",
		description: "Search by member name or loan number",
		placeholder: "Search...",
	},
};

export const Disabled: Story = {
	args: {
		label: "Rate",
		placeholder: "6.25%",
		disabled: true,
	},
};
