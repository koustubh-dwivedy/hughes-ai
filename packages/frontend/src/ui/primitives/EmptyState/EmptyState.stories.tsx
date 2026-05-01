import type { Meta, StoryObj } from "@storybook/react";
import EmptyState from "./EmptyState";

const meta: Meta<typeof EmptyState> = {
	component: EmptyState,
	parameters: { layout: "centered" },
};
export default meta;

type Story = StoryObj<typeof EmptyState>;

export const HeadlineOnly: Story = {
	args: { headline: "No data available" },
};

export const WithBody: Story = {
	args: {
		headline: "No loans found",
		body: "There are no loans matching the current filters.",
	},
};

export const WithAction: Story = {
	args: {
		headline: "No results",
		body: "Try broadening your search criteria.",
		action: { label: "Reset filters", onClick: () => undefined },
	},
};

export const WithIcon: Story = {
	render: () => (
		<EmptyState
			headline="Nothing here yet"
			icon={
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					strokeWidth={2}
				>
					<title>Info</title>
					<circle cx="12" cy="12" r="10" />
					<path d="M12 8v4m0 4h.01" />
				</svg>
			}
		/>
	),
};

export const Full: Story = {
	render: () => (
		<EmptyState
			headline="No loan applications"
			body="Submit a new application to get started."
			action={{ label: "New application", onClick: () => undefined }}
			icon={
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					strokeWidth={2}
				>
					<title>Document</title>
					<path d="M9 12h6m-3-3v6M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z" />
				</svg>
			}
		/>
	),
};
