import { Button } from "@mantine/core";
import type { Meta, StoryObj } from "@storybook/react";
import Popover, { PopoverDropdown, PopoverTarget } from "./Popover";

const meta: Meta<typeof Popover> = {
	component: Popover,
	title: "Primitives/Popover",
};
export default meta;
type Story = StoryObj<typeof Popover>;

export const Basic: Story = {
	render: () => (
		<Popover>
			<PopoverTarget>
				<Button>Open popover</Button>
			</PopoverTarget>
			<PopoverDropdown>
				<p style={{ margin: 0, padding: "0.5rem" }}>Popover content here.</p>
			</PopoverDropdown>
		</Popover>
	),
};

export const NoArrow: Story = {
	render: () => (
		<Popover withArrow={false}>
			<PopoverTarget>
				<Button variant="outline">No arrow</Button>
			</PopoverTarget>
			<PopoverDropdown>
				<p style={{ margin: 0, padding: "0.5rem" }}>No arrow variant.</p>
			</PopoverDropdown>
		</Popover>
	),
};

export const WithForm: Story = {
	render: () => (
		<Popover>
			<PopoverTarget>
				<Button>Open form</Button>
			</PopoverTarget>
			<PopoverDropdown>
				<div
					style={{
						padding: "1rem",
						display: "flex",
						flexDirection: "column",
						gap: "0.5rem",
					}}
				>
					<label htmlFor="email">Email</label>
					<input id="email" type="email" placeholder="you@example.com" />
					<Button size="sm">Submit</Button>
				</div>
			</PopoverDropdown>
		</Popover>
	),
};
