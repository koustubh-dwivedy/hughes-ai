import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import SideNav from "../app/SideNav";
import { renderWithProviders } from "./test-utils";

function renderAt(path: string) {
	return renderWithProviders(
		<MemoryRouter initialEntries={[path]}>
			<SideNav />
		</MemoryRouter>,
	);
}

describe("SideNav", () => {
	it("renders the lending product nav (1 intelligence + 4 dashboards + 2 data + switch) + Hughes logo home link", () => {
		renderAt("/dashboards/executive");
		// 7 lending nav items + "Switch product" + 1 Hughes-logo-as-home anchor = 9.
		expect(screen.getAllByRole("link")).toHaveLength(9);
	});

	it("scopes the sidebar to the Dispute Center product at /disputes", () => {
		renderAt("/disputes");
		// Only the dispute nav + switch product + logo are shown; no lending nav.
		expect(
			screen.getByRole("link", { name: "Case Queue" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("link", { name: "Switch product" }),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("link", { name: "Executive Summary" }),
		).not.toBeInTheDocument();
	});

	it("shows the Switch product control in the lending product", () => {
		renderAt("/dashboards/executive");
		expect(
			screen.getByRole("link", { name: "Switch product" }),
		).toHaveAttribute("href", "/");
		expect(
			screen.queryByRole("link", { name: "Case Queue" }),
		).not.toBeInTheDocument();
	});

	it("marks Data Models active at /data/models", () => {
		renderAt("/data/models");
		expect(screen.getByRole("link", { name: "Data Models" })).toHaveAttribute(
			"aria-current",
			"page",
		);
	});

	it("marks Executive Summary active at /dashboards/executive", () => {
		renderAt("/dashboards/executive");
		expect(
			screen.getByRole("link", { name: "Executive Summary" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("marks Data Intelligence active at /intelligence", () => {
		renderAt("/intelligence");
		expect(
			screen.getByRole("link", { name: "Data Intelligence" }),
		).toHaveAttribute("aria-current", "page");
		expect(
			screen.getByRole("link", { name: "Executive Summary" }),
		).not.toHaveAttribute("aria-current");
	});

	it("marks Sources & Freshness active at /data/sources", () => {
		renderAt("/data/sources");
		expect(
			screen.getByRole("link", { name: "Sources & Freshness" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("marks Deposit Portfolio active at /dashboards/deposits", () => {
		renderAt("/dashboards/deposits");
		expect(
			screen.getByRole("link", { name: "Deposit Portfolio" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("marks Past Due active at /dashboards/past-due", () => {
		renderAt("/dashboards/past-due");
		expect(screen.getByRole("link", { name: "Past Due" })).toHaveAttribute(
			"aria-current",
			"page",
		);
	});

	it("marks Officer/Branch active at /dashboards/officer-branch", () => {
		renderAt("/dashboards/officer-branch");
		expect(
			screen.getByRole("link", { name: "Officer/Branch" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("does not mark Executive Summary active at /dashboards/deposits", () => {
		renderAt("/dashboards/deposits");
		expect(
			screen.getByRole("link", { name: "Executive Summary" }),
		).not.toHaveAttribute("aria-current");
	});

	it("shows the Hughes AI logo", () => {
		renderAt("/dashboards/executive");
		expect(screen.getByAltText("Hughes AI")).toBeInTheDocument();
	});

	it("renders nav with accessible label", () => {
		renderAt("/dashboards/executive");
		expect(
			screen.getByRole("navigation", { name: "primary" }),
		).toBeInTheDocument();
	});
});
