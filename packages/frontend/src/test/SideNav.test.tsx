import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import SideNav from "../app/SideNav";

function renderAt(path: string) {
	return render(
		<MemoryRouter initialEntries={[path]}>
			<SideNav />
		</MemoryRouter>,
	);
}

describe("SideNav", () => {
	it("renders 5 nav links", () => {
		renderAt("/dashboards/executive");
		expect(screen.getAllByRole("link")).toHaveLength(5);
	});

	it("marks Executive Summary active at /dashboards/executive", () => {
		renderAt("/dashboards/executive");
		expect(
			screen.getByRole("link", { name: "Executive Summary" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("marks Chat active at /chat", () => {
		renderAt("/chat");
		expect(screen.getByRole("link", { name: "Chat" })).toHaveAttribute(
			"aria-current",
			"page",
		);
		expect(
			screen.getByRole("link", { name: "Executive Summary" }),
		).not.toHaveAttribute("aria-current");
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

	it("shows Hughes AI wordmark", () => {
		renderAt("/dashboards/executive");
		expect(screen.getByText("Hughes AI")).toBeInTheDocument();
	});

	it("renders nav with accessible label", () => {
		renderAt("/dashboards/executive");
		expect(
			screen.getByRole("navigation", { name: "primary" }),
		).toBeInTheDocument();
	});
});
