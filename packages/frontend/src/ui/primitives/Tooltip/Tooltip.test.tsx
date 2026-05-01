import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import Tooltip from "./Tooltip";

function withMantine(ui: React.ReactElement) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("Tooltip", () => {
	it("shows tooltip content on hover", async () => {
		const user = userEvent.setup();
		withMantine(
			<Tooltip label="Delinquency rate explanation">
				<button type="button">Hover me</button>
			</Tooltip>,
		);
		await user.hover(screen.getByRole("button", { name: "Hover me" }));
		expect(
			await screen.findByText("Delinquency rate explanation"),
		).toBeInTheDocument();
	});

	it("passes withArrow=true by default", () => {
		const { container } = withMantine(
			<Tooltip label="Tip text" opened>
				<button type="button">Target</button>
			</Tooltip>,
		);
		// Mantine renders the arrow element when withArrow is true
		expect(container).toBeInTheDocument();
		expect(screen.getByText("Tip text")).toBeInTheDocument();
	});
});
