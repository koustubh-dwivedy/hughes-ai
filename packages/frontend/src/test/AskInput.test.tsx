import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AskInput from "../features/chat/AskInput";

describe("AskInput", () => {
	it("renders with Ask button disabled when input is empty", () => {
		render(<AskInput onSubmit={vi.fn()} loading={false} />);
		expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
	});

	it("enables the button after typing", async () => {
		const user = userEvent.setup();
		render(<AskInput onSubmit={vi.fn()} loading={false} />);
		await user.type(screen.getByRole("textbox"), "how many loans");
		expect(screen.getByRole("button", { name: "Ask" })).toBeEnabled();
	});

	it("calls onSubmit with trimmed question text on click", async () => {
		const user = userEvent.setup();
		const onSubmit = vi.fn();
		render(<AskInput onSubmit={onSubmit} loading={false} />);
		await user.type(screen.getByRole("textbox"), "  how many loans  ");
		await user.click(screen.getByRole("button", { name: "Ask" }));
		expect(onSubmit).toHaveBeenCalledOnce();
		expect(onSubmit).toHaveBeenCalledWith("how many loans");
	});

	it("calls onSubmit on Enter key", async () => {
		const user = userEvent.setup();
		const onSubmit = vi.fn();
		render(<AskInput onSubmit={onSubmit} loading={false} />);
		await user.type(screen.getByRole("textbox"), "approval rate{Enter}");
		expect(onSubmit).toHaveBeenCalledWith("approval rate");
	});

	it("shows Loading… and disables button when loading=true", () => {
		render(<AskInput onSubmit={vi.fn()} loading={true} />);
		expect(screen.getByRole("button", { name: "Loading…" })).toBeDisabled();
		expect(screen.getByRole("textbox")).toBeDisabled();
	});
});
