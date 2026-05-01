import type { Meta, StoryObj } from "@storybook/react";
import ErrorState from "./ErrorState";

const meta: Meta<typeof ErrorState> = {
	component: ErrorState,
	parameters: { layout: "centered" },
};
export default meta;

type Story = StoryObj<typeof ErrorState>;

export const WithRetry: Story = {
	args: {
		message: "The request timed out. Please try again.",
		onRetry: () => undefined,
	},
};

export const NoRetry: Story = {
	args: {
		message:
			"An unexpected error occurred. Contact support if the issue persists.",
	},
};

export const LongMessage: Story = {
	args: {
		title: "Dashboard unavailable",
		message:
			"We were unable to load the executive summary dashboard. This may be due to a temporary outage or network issue. Please wait a moment and try again. If the problem continues, contact your system administrator.",
		onRetry: () => undefined,
	},
};
