import type { Meta, StoryObj } from "@storybook/react";
import Banner from "./Banner";

const meta: Meta<typeof Banner> = {
	component: Banner,
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof Banner>;

export const Info: Story = {
	args: { message: "This is an informational banner.", variant: "info" },
};

export const Warning: Story = {
	args: { message: "This is a warning banner.", variant: "warning" },
};
