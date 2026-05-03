import { fireEvent, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import SideNav from "./SideNav";

function renderAt(path = "/dashboards/executive") {
	return renderWithProviders(
		<MemoryRouter initialEntries={[path]}>
			<SideNav />
		</MemoryRouter>,
	);
}

describe("SideNav collapse states", () => {
	it("starts in full state by default (data-collapsed=false)", () => {
		renderAt();
		const nav = screen.getByRole("navigation", { name: "primary" });
		expect(nav).toHaveAttribute("data-collapsed", "false");
	});

	it("starts collapsed when defaultCollapsed=true", () => {
		renderWithProviders(
			<MemoryRouter initialEntries={["/dashboards/executive"]}>
				<SideNav defaultCollapsed />
			</MemoryRouter>,
		);
		const nav = screen.getByRole("navigation", { name: "primary" });
		expect(nav).toHaveAttribute("data-collapsed", "true");
	});

	it("collapses when toggle button is clicked", () => {
		renderAt();
		const toggle = screen.getByRole("button", { name: "Collapse sidebar" });
		fireEvent.click(toggle);
		const nav = screen.getByRole("navigation", { name: "primary" });
		expect(nav).toHaveAttribute("data-collapsed", "true");
	});

	it("expands when toggle is clicked again", () => {
		renderAt();
		const toggle = screen.getByRole("button", { name: "Collapse sidebar" });
		fireEvent.click(toggle);
		const expandToggle = screen.getByRole("button", { name: "Expand sidebar" });
		fireEvent.click(expandToggle);
		const nav = screen.getByRole("navigation", { name: "primary" });
		expect(nav).toHaveAttribute("data-collapsed", "false");
	});

	it("hides nav labels when collapsed", () => {
		renderAt();
		fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
		expect(screen.queryByText("Executive Summary")).toBeNull();
	});

	it("shows nav labels when full", () => {
		renderAt();
		expect(screen.getByText("Executive Summary")).toBeInTheDocument();
	});
});

describe("SideNav active indication", () => {
	it("marks Executive Summary active at /dashboards/executive", () => {
		renderAt("/dashboards/executive");
		expect(
			screen.getByRole("link", { name: /Executive Summary/i }),
		).toHaveAttribute("aria-current", "page");
	});

	it("marks Data Intelligence active at /intelligence", () => {
		renderAt("/intelligence");
		expect(
			screen.getByRole("link", { name: /Data Intelligence/i }),
		).toHaveAttribute("aria-current", "page");
	});

	it("does not mark Executive Summary active when at /dashboards/deposits", () => {
		renderAt("/dashboards/deposits");
		expect(
			screen.getByRole("link", { name: /Executive Summary/i }),
		).not.toHaveAttribute("aria-current");
	});
});

describe("SideNav drawer", () => {
	it("hamburger button opens navigation drawer", () => {
		renderAt();
		const hamburger = screen.getByTestId("hamburger");
		fireEvent.click(hamburger);
		expect(
			screen.getByRole("dialog", { name: "Navigation drawer" }),
		).toBeInTheDocument();
	});

	it("close button dismisses the drawer", () => {
		renderAt();
		fireEvent.click(screen.getByTestId("hamburger"));
		const closeBtn = screen.getAllByRole("button", {
			name: "Close navigation",
		});
		fireEvent.click(closeBtn[0]);
		expect(
			screen.queryByRole("dialog", { name: "Navigation drawer" }),
		).toBeNull();
	});
});
