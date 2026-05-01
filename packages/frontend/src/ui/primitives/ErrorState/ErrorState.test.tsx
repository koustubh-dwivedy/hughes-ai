import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ErrorState from "./ErrorState";

describe("ErrorState", () => {
	it("has role=alert", () => {
		render(<ErrorState message="Something failed." />);
		expect(screen.getByRole("alert")).toBeInTheDocument();
	});

	it("renders the message", () => {
		render(<ErrorState message="Could not load data." />);
		expect(screen.getByText("Could not load data.")).toBeInTheDocument();
	});

	it("renders default title when title omitted", () => {
		render(<ErrorState message="Error" />);
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();
	});

	it("renders custom title", () => {
		render(<ErrorState message="Error" title="Load failed" />);
		expect(screen.getByText("Load failed")).toBeInTheDocument();
	});

	it("renders retry button when onRetry provided and fires callback", async () => {
		const user = userEvent.setup();
		const onRetry = vi.fn();
		render(<ErrorState message="Error" onRetry={onRetry} />);
		const btn = screen.getByRole("button", { name: "Try again" });
		expect(btn).toBeInTheDocument();
		await user.click(btn);
		expect(onRetry).toHaveBeenCalledOnce();
	});

	it("does not render retry button when onRetry is absent", () => {
		render(<ErrorState message="Error" />);
		expect(screen.queryByRole("button")).toBeNull();
	});
});
