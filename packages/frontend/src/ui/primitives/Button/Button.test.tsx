import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Button from "./Button";

function withMantine(ui: React.ReactElement) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("Button", () => {
	it("renders with label", () => {
		withMantine(<Button>Submit</Button>);
		expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
	});

	it("fires onClick when clicked", async () => {
		const user = userEvent.setup();
		const onClick = vi.fn();
		withMantine(<Button onClick={onClick}>Click Me</Button>);
		await user.click(screen.getByRole("button", { name: "Click Me" }));
		expect(onClick).toHaveBeenCalledTimes(1);
	});

	it("is disabled when disabled prop is set", () => {
		withMantine(<Button disabled>Disabled</Button>);
		expect(screen.getByRole("button", { name: "Disabled" })).toBeDisabled();
	});

	it("has default variant filled", () => {
		withMantine(<Button>Default</Button>);
		const btn = screen.getByRole("button", { name: "Default" });
		expect(btn).toBeInTheDocument();
		// Mantine applies data-variant attribute for filled
		expect(btn).toHaveAttribute("data-variant", "filled");
	});
});
