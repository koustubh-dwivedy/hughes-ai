import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import SideNav from "../layout/SideNav";

function renderAt(path: string) {
	return render(
		<MemoryRouter initialEntries={[path]}>
			<SideNav />
		</MemoryRouter>,
	);
}

describe("SideNav", () => {
	it("renders 5 nav links", () => {
		renderAt("/");
		expect(screen.getAllByRole("link")).toHaveLength(5);
	});

	it("marks Executive Summary active at /", () => {
		renderAt("/");
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

	it("marks Deposit Portfolio active at /deposits", () => {
		renderAt("/deposits");
		expect(
			screen.getByRole("link", { name: "Deposit Portfolio" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("marks Past Due active at /past-due", () => {
		renderAt("/past-due");
		expect(screen.getByRole("link", { name: "Past Due" })).toHaveAttribute(
			"aria-current",
			"page",
		);
	});

	it("marks Officer/Branch active at /officers", () => {
		renderAt("/officers");
		expect(
			screen.getByRole("link", { name: "Officer/Branch" }),
		).toHaveAttribute("aria-current", "page");
	});

	it("does not mark Executive Summary active at /deposits", () => {
		renderAt("/deposits");
		expect(
			screen.getByRole("link", { name: "Executive Summary" }),
		).not.toHaveAttribute("aria-current");
	});

	it("shows Hughes AI wordmark", () => {
		renderAt("/");
		expect(screen.getByText("Hughes AI")).toBeInTheDocument();
	});

	it("renders nav with accessible label", () => {
		renderAt("/");
		expect(
			screen.getByRole("navigation", { name: "primary" }),
		).toBeInTheDocument();
	});
});
