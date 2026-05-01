import type { Meta, StoryObj } from "@storybook/react";
import PageHeader from "./PageHeader";

const meta: Meta<typeof PageHeader> = {
	component: PageHeader,
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof PageHeader>;

export const TitleOnly: Story = {
	args: { title: "Loan Portfolio" },
};

export const WithEyebrow: Story = {
	args: { title: "Loan Portfolio", eyebrow: "Dashboard" },
};

export const WithSubtitle: Story = {
	args: {
		title: "Loan Portfolio",
		eyebrow: "Dashboard",
		subtitle: "Origination and performance metrics",
	},
};

export const WithActions: Story = {
	args: {
		title: "Loan Portfolio",
		actions: <button type="button">Export</button>,
	},
};

export const WithDateBadge: Story = {
	args: {
		title: "Loan Portfolio",
		dateBadge: <span>As of Apr 30, 2026</span>,
	},
};

export const Full: Story = {
	args: {
		eyebrow: "Dashboard",
		title: "Loan Portfolio",
		subtitle: "Origination and performance metrics for small_cu",
		dateBadge: <span>As of Apr 30, 2026</span>,
		actions: <button type="button">Export CSV</button>,
	},
};
