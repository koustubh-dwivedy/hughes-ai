import type { Meta, StoryObj } from "@storybook/react";
import KpiTile from "./KpiTile";

const meta: Meta<typeof KpiTile> = {
	component: KpiTile,
	title: "Primitives/KpiTile",
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof KpiTile>;

export const Default: Story = {
	args: {
		label: "Total Loans",
		value: "$42.5M",
	},
};

export const WithDeltaPositive: Story = {
	args: {
		label: "Total Loans",
		value: "$42.5M",
		delta: "↑ $1.4M",
		deltaLabel: "MoM",
		deltaPositive: true,
	},
};

export const WithDeltaNegative: Story = {
	args: {
		label: "Past Due Ratio",
		value: "1.8%",
		delta: "↑ 0.3 pp",
		deltaLabel: "MoM",
		deltaPositive: false,
	},
};

export const WithContext: Story = {
	args: {
		label: "Total Loans",
		value: "$42.5M",
		delta: "↑ $1.4M",
		deltaLabel: "MoM",
		deltaPositive: true,
		context: "Fastest growth in six months",
	},
};

export const WithIcon: Story = {
	args: {
		label: "Active Members",
		value: "2,847",
		icon: "👥",
	},
};

export const WithInfoTooltip: Story = {
	args: {
		label: "Past Due Ratio",
		value: "1.4%",
		delta: "↓ 0.1 pp",
		deltaLabel: "MoM",
		deltaPositive: true,
		infoTooltip:
			"Share of loan balance 30+ days late. Industry healthy band: under 1.5%.",
	},
};

export const Clickable: Story = {
	args: {
		label: "Total Loans",
		value: "$42.5M",
		delta: "↑ $1.4M",
		deltaLabel: "MoM",
		deltaPositive: true,
		onClick: () => undefined,
	},
};

export const Loading: Story = {
	args: {
		label: "Total Loans",
		value: "$42.5M",
		loading: true,
	},
};

export const AllFeatures: Story = {
	args: {
		label: "Total Loans",
		value: "$142.5M",
		delta: "↑ $1.4M",
		deltaLabel: "MoM",
		deltaPositive: true,
		context: "Fastest growth in six months",
		icon: "💼",
		infoTooltip: "Outstanding loan balance across all active accounts.",
		onClick: () => undefined,
	},
};
