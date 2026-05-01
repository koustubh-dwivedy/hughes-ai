import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter } from "react-router-dom";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import AppHeader from "./AppHeader";

const meta: Meta<typeof AppHeader> = {
	component: AppHeader,
	title: "App/AppHeader",
	parameters: { layout: "fullscreen" },
	decorators: [
		(Story) => (
			<MemoryRouter initialEntries={["/?as_of_date=2026-04-30"]}>
				<DashboardContextProvider>
					<Story />
				</DashboardContextProvider>
			</MemoryRouter>
		),
	],
};
export default meta;

type Story = StoryObj<typeof AppHeader>;

export const WithDate: Story = {};

export const NoDate: Story = {
	decorators: [
		(Story) => (
			<MemoryRouter initialEntries={["/"]}>
				<DashboardContextProvider>
					<Story />
				</DashboardContextProvider>
			</MemoryRouter>
		),
	],
};
