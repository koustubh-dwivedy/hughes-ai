import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PageHeader from "./PageHeader";

describe("PageHeader", () => {
	it("renders title in an h1", () => {
		render(<PageHeader title="Loan Portfolio" />);
		const heading = screen.getByRole("heading", { level: 1 });
		expect(heading).toHaveTextContent("Loan Portfolio");
	});

	it("shows eyebrow when provided", () => {
		render(<PageHeader title="Overview" eyebrow="Dashboard" />);
		expect(screen.getByText("Dashboard")).toBeInTheDocument();
	});

	it("shows subtitle when provided", () => {
		render(<PageHeader title="Overview" subtitle="Last 30 days" />);
		expect(screen.getByText("Last 30 days")).toBeInTheDocument();
	});

	it("renders actions slot content in the DOM", () => {
		render(
			<PageHeader
				title="Overview"
				actions={<button type="button">Export</button>}
			/>,
		);
		expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
	});

	it("renders dateBadge slot content in the DOM", () => {
		render(
			<PageHeader
				title="Overview"
				dateBadge={<span>As of Apr 30, 2026</span>}
			/>,
		);
		expect(screen.getByText("As of Apr 30, 2026")).toBeInTheDocument();
	});
});
