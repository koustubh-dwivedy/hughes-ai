import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import Popover, { PopoverDropdown, PopoverTarget } from "./Popover";

function withMantine(ui: React.ReactElement) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("Popover", () => {
	it("trigger button has aria-expanded=false when closed", () => {
		withMantine(
			<Popover>
				<PopoverTarget>
					<button type="button">Open Popover</button>
				</PopoverTarget>
				<PopoverDropdown>
					<p>Content</p>
				</PopoverDropdown>
			</Popover>,
		);
		const btn = screen.getByRole("button", { name: "Open Popover" });
		expect(btn).toHaveAttribute("aria-expanded", "false");
	});

	it("opens on trigger click — aria-expanded becomes true", async () => {
		const user = userEvent.setup();
		withMantine(
			<Popover>
				<PopoverTarget>
					<button type="button">Toggle</button>
				</PopoverTarget>
				<PopoverDropdown>
					<p>Content</p>
				</PopoverDropdown>
			</Popover>,
		);
		const btn = screen.getByRole("button", { name: "Toggle" });
		await user.click(btn);
		expect(btn).toHaveAttribute("aria-expanded", "true");
	});

	it("closes on second click — aria-expanded returns to false", async () => {
		const user = userEvent.setup();
		withMantine(
			<Popover>
				<PopoverTarget>
					<button type="button">Toggle</button>
				</PopoverTarget>
				<PopoverDropdown>
					<p>Content</p>
				</PopoverDropdown>
			</Popover>,
		);
		const btn = screen.getByRole("button", { name: "Toggle" });
		await user.click(btn);
		expect(btn).toHaveAttribute("aria-expanded", "true");
		await user.click(btn);
		expect(btn).toHaveAttribute("aria-expanded", "false");
	});
});
