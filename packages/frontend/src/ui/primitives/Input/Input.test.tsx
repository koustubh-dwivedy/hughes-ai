import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Input from "./Input";

function withMantine(ui: React.ReactElement) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("Input", () => {
	it("renders with placeholder", () => {
		withMantine(<Input placeholder="Search loans..." />);
		expect(screen.getByPlaceholderText("Search loans...")).toBeInTheDocument();
	});

	it("fires onChange with typed value", async () => {
		const user = userEvent.setup();
		const onChange = vi.fn();
		withMantine(<Input placeholder="Type here" onChange={onChange} />);
		const input = screen.getByPlaceholderText("Type here");
		await user.type(input, "hello");
		expect(onChange).toHaveBeenCalled();
	});

	it("renders accessible label when label prop is provided", () => {
		withMantine(<Input label="Loan Amount" placeholder="0.00" />);
		expect(screen.getByLabelText("Loan Amount")).toBeInTheDocument();
	});

	it("shows error message when error prop is provided", () => {
		withMantine(<Input label="Amount" error="This field is required" />);
		expect(screen.getByText("This field is required")).toBeInTheDocument();
	});
});
