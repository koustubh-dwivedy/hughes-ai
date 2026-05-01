import type { Meta, StoryObj } from "@storybook/react";
import Skeleton from "./Skeleton";

const meta: Meta<typeof Skeleton> = {
	component: Skeleton,
	parameters: { layout: "padded" },
};
export default meta;

type Story = StoryObj<typeof Skeleton>;

export const TextLine: Story = {
	args: { width: "60%", height: "1rem" },
};

export const Circle: Story = {
	args: { width: 48, height: 48, borderRadius: "9999px" },
};

export const Card: Story = {
	args: { width: "100%", height: "8rem", borderRadius: "0.5rem" },
};

export const Grid: Story = {
	render: () => (
		<div
			style={{
				display: "grid",
				gridTemplateColumns: "1fr 1fr 1fr",
				gap: "1rem",
			}}
		>
			<Skeleton height="5rem" />
			<Skeleton height="5rem" />
			<Skeleton height="5rem" />
		</div>
	),
};

export const Paragraph: Story = {
	render: () => (
		<div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
			<Skeleton width="100%" height="1rem" />
			<Skeleton width="85%" height="1rem" />
			<Skeleton width="90%" height="1rem" />
			<Skeleton width="60%" height="1rem" />
		</div>
	),
};
