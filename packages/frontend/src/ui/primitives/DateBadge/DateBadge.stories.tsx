import type { Meta, StoryObj } from "@storybook/react";
import DateBadge from "./DateBadge";

const meta: Meta<typeof DateBadge> = {
	component: DateBadge,
	parameters: { layout: "centered" },
};
export default meta;

type Story = StoryObj<typeof DateBadge>;

export const AsOfOnly: Story = {
	args: { asOfDate: "2026-04-30" },
};

export const WithRefresh: Story = {
	args: {
		asOfDate: "2026-04-30",
		refreshedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
	},
};

export const WithTooltip: Story = {
	args: {
		asOfDate: "2026-04-30",
		tooltip: "Data is updated nightly at midnight",
	},
};

export const LiveExample: Story = {
	args: {
		asOfDate: "2026-04-30",
		refreshedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
		tooltip: "Data refreshes every 24 hours",
	},
};
