import type { Meta, StoryObj } from "@storybook/react";
import Tabs, { TabsList, TabsPanel, TabsTab } from "./Tabs";

const meta: Meta<typeof Tabs> = {
	component: Tabs,
	title: "Primitives/Tabs",
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof Tabs>;

export const Basic: Story = {
	render: () => (
		<Tabs defaultValue="overview">
			<TabsList>
				<TabsTab value="overview">Overview</TabsTab>
				<TabsTab value="details">Details</TabsTab>
			</TabsList>
			<TabsPanel value="overview" pt="md">
				Overview panel content
			</TabsPanel>
			<TabsPanel value="details" pt="md">
				Details panel content
			</TabsPanel>
		</Tabs>
	),
};

export const Controlled: Story = {
	render: () => (
		<Tabs value="details">
			<TabsList>
				<TabsTab value="overview">Overview</TabsTab>
				<TabsTab value="details">Details</TabsTab>
			</TabsList>
			<TabsPanel value="overview" pt="md">
				Overview panel content
			</TabsPanel>
			<TabsPanel value="details" pt="md">
				Details panel content (active)
			</TabsPanel>
		</Tabs>
	),
};

export const ThreeTabs: Story = {
	render: () => (
		<Tabs defaultValue="loans">
			<TabsList>
				<TabsTab value="loans">Loans</TabsTab>
				<TabsTab value="deposits">Deposits</TabsTab>
				<TabsTab value="members">Members</TabsTab>
			</TabsList>
			<TabsPanel value="loans" pt="md">
				Loans content
			</TabsPanel>
			<TabsPanel value="deposits" pt="md">
				Deposits content
			</TabsPanel>
			<TabsPanel value="members" pt="md">
				Members content
			</TabsPanel>
		</Tabs>
	),
};

export const WithIcons: Story = {
	render: () => (
		<Tabs defaultValue="portfolio">
			<TabsList>
				<TabsTab value="portfolio">📊 Portfolio</TabsTab>
				<TabsTab value="pastdue">⚠️ Past Due</TabsTab>
			</TabsList>
			<TabsPanel value="portfolio" pt="md">
				Portfolio panel
			</TabsPanel>
			<TabsPanel value="pastdue" pt="md">
				Past due panel
			</TabsPanel>
		</Tabs>
	),
};
