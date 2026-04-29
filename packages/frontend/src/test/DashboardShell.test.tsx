import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DashboardShell from "../layout/DashboardShell";

vi.mock("../lib/logger", () => ({
	default: { warn: vi.fn(), error: vi.fn() },
}));

describe("DashboardShell", () => {
	it("renders the title as a heading", () => {
		render(
			<DashboardShell title="Deposit Portfolio">
				<div>content</div>
			</DashboardShell>,
		);
		expect(
			screen.getByRole("heading", { name: "Deposit Portfolio" }),
		).toBeInTheDocument();
	});

	it("renders as_of_date when provided", () => {
		render(
			<DashboardShell title="Test" as_of_date="2024-03-31">
				<div>content</div>
			</DashboardShell>,
		);
		expect(screen.getByText("As of 2024-03-31")).toBeInTheDocument();
	});

	it("shows loading status and hides children when loading=true", () => {
		render(
			<DashboardShell title="Test" loading={true}>
				<div>hidden-content</div>
			</DashboardShell>,
		);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByText("hidden-content")).toBeNull();
	});

	it("shows error alert when error is set", () => {
		render(
			<DashboardShell title="Test" error="Failed to load">
				<div>hidden-content</div>
			</DashboardShell>,
		);
		expect(screen.getByRole("alert")).toBeInTheDocument();
		expect(screen.getByText("Failed to load")).toBeInTheDocument();
		expect(screen.queryByText("hidden-content")).toBeNull();
	});

	it("shows empty state when empty=true", () => {
		render(
			<DashboardShell title="Test" empty={true}>
				<div>hidden-content</div>
			</DashboardShell>,
		);
		expect(screen.getByText("No data available.")).toBeInTheDocument();
		expect(screen.queryByText("hidden-content")).toBeNull();
	});

	it("renders children in default state", () => {
		render(
			<DashboardShell title="Test">
				<div>my-content</div>
			</DashboardShell>,
		);
		expect(screen.getByText("my-content")).toBeInTheDocument();
	});

	it("loading takes priority over error", () => {
		render(
			<DashboardShell title="Test" loading={true} error="oops">
				<div>content</div>
			</DashboardShell>,
		);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("alert")).toBeNull();
	});
});
