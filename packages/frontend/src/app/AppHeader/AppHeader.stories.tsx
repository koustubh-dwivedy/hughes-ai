import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter } from "react-router-dom";
import AppHeader from "./AppHeader";

const meta: Meta<typeof AppHeader> = {
	component: AppHeader,
	title: "App/AppHeader",
	parameters: { layout: "fullscreen" },
	decorators: [
		(Story) => (
			<MemoryRouter>
				<Story />
			</MemoryRouter>
		),
	],
};
export default meta;

type Story = StoryObj<typeof AppHeader>;

export const Default: Story = {};
