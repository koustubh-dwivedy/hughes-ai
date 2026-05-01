import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { DashboardContextProvider } from "../../shared/context/DashboardContext";
import { renderWithProviders } from "../../test/test-utils";
import AppHeader from "./AppHeader";

function renderHeader(initialPath = "/") {
	return renderWithProviders(
		<MemoryRouter initialEntries={[initialPath]}>
			<DashboardContextProvider>
				<AppHeader />
			</DashboardContextProvider>
		</MemoryRouter>,
	);
}

describe("AppHeader", () => {
	it("renders the workspace badge", () => {
		renderHeader();
		expect(screen.getByText("Hughes AI")).toBeInTheDocument();
	});

	it("renders the search trigger with ⌘K hint", () => {
		renderHeader();
		expect(
			screen.getByRole("button", { name: "Open search" }),
		).toBeInTheDocument();
		expect(screen.getByText("⌘K")).toBeInTheDocument();
	});

	it("renders the user menu button", () => {
		renderHeader();
		expect(
			screen.getByRole("button", { name: "User menu" }),
		).toBeInTheDocument();
	});

	it("shows 'Select date' when no as-of-date in URL", () => {
		renderHeader();
		expect(screen.getByText(/Select date/)).toBeInTheDocument();
	});

	it("shows as-of-date when URL has as_of_date param", () => {
		renderHeader("/?as_of_date=2026-04-30");
		expect(screen.getByText(/2026-04-30/)).toBeInTheDocument();
	});

	it("date picker button is accessible", () => {
		renderHeader();
		expect(
			screen.getByRole("button", { name: "Select as-of date" }),
		).toBeInTheDocument();
	});

	it("clicking date picker opens preset popover", async () => {
		renderHeader();
		fireEvent.click(screen.getByRole("button", { name: "Select as-of date" }));
		await waitFor(() => {
			expect(screen.getByText("Today")).toBeInTheDocument();
		});
		expect(screen.getByText("Start of Month")).toBeInTheDocument();
		expect(screen.getByText("Last Month")).toBeInTheDocument();
	});
});
