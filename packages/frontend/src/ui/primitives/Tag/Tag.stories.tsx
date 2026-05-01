import type { Meta, StoryObj } from "@storybook/react";
import Tag from "./Tag";

const meta: Meta<typeof Tag> = {
	component: Tag,
	parameters: { layout: "centered" },
};
export default meta;

type Story = StoryObj<typeof Tag>;

export const AllVariants: Story = {
	render: () => (
		<div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
			<Tag label="Default" variant="default" />
			<Tag label="Success" variant="success" />
			<Tag label="Warning" variant="warning" />
			<Tag label="Danger" variant="danger" />
			<Tag label="Info" variant="info" />
		</div>
	),
};

export const Sizes: Story = {
	render: () => (
		<div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
			<Tag label="Small" size="sm" />
			<Tag label="Medium" size="md" />
		</div>
	),
};

export const Removable: Story = {
	render: () => (
		<div style={{ display: "flex", gap: "0.5rem" }}>
			<Tag label="Auto" variant="info" onRemove={() => undefined} />
			<Tag label="Home" variant="success" onRemove={() => undefined} />
			<Tag label="Past Due" variant="danger" onRemove={() => undefined} />
		</div>
	),
};

export const CaveatExample: Story = {
	render: () => (
		<div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
			<Tag label="Watchlist" variant="warning" />
			<Tag label="Delinquent 30+" variant="danger" />
			<Tag label="Current" variant="success" />
			<Tag label="Under Review" variant="info" />
			<Tag label="Closed" variant="default" />
		</div>
	),
};
