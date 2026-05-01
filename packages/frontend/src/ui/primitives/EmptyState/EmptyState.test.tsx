import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import EmptyState from "./EmptyState";

describe("EmptyState", () => {
	it("renders the headline", () => {
		render(<EmptyState headline="No results found" />);
		expect(screen.getByText("No results found")).toBeInTheDocument();
	});

	it("renders body text when provided", () => {
		render(<EmptyState headline="Empty" body="Try adjusting your filters." />);
		expect(screen.getByText("Try adjusting your filters.")).toBeInTheDocument();
	});

	it("does not render body when omitted", () => {
		render(<EmptyState headline="Empty" />);
		expect(screen.queryByText(/Try/)).toBeNull();
	});

	it("renders action button and fires onClick", async () => {
		const user = userEvent.setup();
		const onClick = vi.fn();
		render(
			<EmptyState headline="Empty" action={{ label: "Refresh", onClick }} />,
		);
		const btn = screen.getByRole("button", { name: "Refresh" });
		expect(btn).toBeInTheDocument();
		await user.click(btn);
		expect(onClick).toHaveBeenCalledOnce();
	});

	it("does not render button when action is omitted", () => {
		render(<EmptyState headline="Empty" />);
		expect(screen.queryByRole("button")).toBeNull();
	});

	it("renders icon slot content", () => {
		render(
			<EmptyState headline="Empty" icon={<span data-testid="icon">★</span>} />,
		);
		expect(screen.getByTestId("icon")).toBeInTheDocument();
	});

	it("has role=status", () => {
		render(<EmptyState headline="No data" />);
		expect(screen.getByRole("status")).toBeInTheDocument();
	});
});
