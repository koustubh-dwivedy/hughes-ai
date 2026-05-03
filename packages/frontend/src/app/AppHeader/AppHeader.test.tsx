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
});
