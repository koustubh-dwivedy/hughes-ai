import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter } from "react-router-dom";
import SideNav from "./SideNav";

const meta: Meta<typeof SideNav> = {
	component: SideNav,
	title: "App/SideNav",
	parameters: { layout: "fullscreen" },
	decorators: [
		(Story) => (
			<MemoryRouter initialEntries={["/dashboards/executive"]}>
				<div style={{ display: "flex", height: "100vh" }}>
					<Story />
					<div style={{ flex: 1, padding: "2rem", background: "#f8fafc" }}>
						Page content area
					</div>
				</div>
			</MemoryRouter>
		),
	],
};
export default meta;

type Story = StoryObj<typeof SideNav>;

export const FullWidth: Story = {
	args: { defaultCollapsed: false },
};

export const Collapsed: Story = {
	args: { defaultCollapsed: true },
};

export const ActiveDeposits: Story = {
	decorators: [
		(Story) => (
			<MemoryRouter initialEntries={["/dashboards/deposits"]}>
				<div style={{ display: "flex", height: "100vh" }}>
					<Story />
					<div style={{ flex: 1, padding: "2rem", background: "#f8fafc" }}>
						Page content area
					</div>
				</div>
			</MemoryRouter>
		),
	],
	args: { defaultCollapsed: false },
};
