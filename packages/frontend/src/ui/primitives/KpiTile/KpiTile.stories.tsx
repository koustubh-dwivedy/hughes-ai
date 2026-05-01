import type { Meta, StoryObj } from "@storybook/react";
import KpiTile from "./KpiTile";

const meta: Meta<typeof KpiTile> = {
	component: KpiTile,
	title: "Primitives/KpiTile",
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof KpiTile>;

const sparklineData = Array.from({ length: 24 }, (_, i) => ({
	value: Math.sin(i / 3) * 10 + 20,
}));

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
		delta: "↑ 4.2%",
		deltaPositive: true,
	},
};

export const WithDeltaNegative: Story = {
	args: {
		label: "Delinquency Rate",
		value: "3.8%",
		delta: "↓ 1.8%",
		deltaPositive: false,
	},
};

export const WithSparkline: Story = {
	args: {
		label: "Loan Balance Trend",
		value: "$42.5M",
		delta: "↑ 2.1%",
		deltaPositive: true,
		sparkline: sparklineData,
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
		label: "Approval Rate",
		value: "78.3%",
		delta: "↑ 1.2%",
		deltaPositive: true,
		infoTooltip:
			"Percentage of loan applications approved in the current period",
	},
};

export const Clickable: Story = {
	args: {
		label: "Total Loans",
		value: "$42.5M",
		delta: "↑ 4.2%",
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
		label: "Portfolio Balance",
		value: "$142.5M",
		delta: "↑ 4.2%",
		deltaPositive: true,
		sparkline: sparklineData,
		icon: "💼",
		infoTooltip: "Total outstanding loan portfolio balance across all products",
		onClick: () => undefined,
	},
};
