import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import AppHeader from "./AppHeader";

function renderHeader() {
	return renderWithProviders(
		<MemoryRouter>
			<AppHeader />
		</MemoryRouter>,
	);
}

describe("AppHeader", () => {
	it("renders the search trigger with ⌘K hint", () => {
		renderHeader();
		expect(
			screen.getByRole("button", { name: "Open search" }),
		).toBeInTheDocument();
		expect(screen.getByText("⌘K")).toBeInTheDocument();
	});

	it("does not render the Hughes AI logo (single logo lives in the sidebar)", () => {
		renderHeader();
		expect(screen.queryByAltText("Hughes AI")).not.toBeInTheDocument();
	});

	it("does not render a user menu button", () => {
		renderHeader();
		expect(
			screen.queryByRole("button", { name: "User menu" }),
		).not.toBeInTheDocument();
	});

	it("does not render a date picker", () => {
		renderHeader();
		expect(
			screen.queryByRole("button", { name: "Select as-of date" }),
		).not.toBeInTheDocument();
	});

	it("renders the workspace name in the header", () => {
		renderHeader();
		expect(
			screen.getByText("Cascade Federal Credit Union"),
		).toBeInTheDocument();
	});

	// Contact Us CTA (originally HUG-270 as "Book a Demo")
	it("renders the Contact Us link with external href + new-tab target", () => {
		renderHeader();
		const link = screen.getByTestId("book-demo-button");
		expect(link).toBeInTheDocument();
		expect(link).toHaveAttribute("href", "https://tryhughes.com/contact.html");
		expect(link).toHaveAttribute("target", "_blank");
		expect(link).toHaveAttribute("rel", "noopener noreferrer");
		expect(link).toHaveAccessibleName(/contact us/i);
	});
});
