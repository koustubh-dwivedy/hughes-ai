import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChartCard from "./ChartCard";

describe("ChartCard", () => {
	it("renders title", () => {
		render(<ChartCard title="Loan Mix">content</ChartCard>);
		expect(screen.getByText("Loan Mix")).toBeInTheDocument();
	});

	it("renders subtitle when provided", () => {
		render(
			<ChartCard title="Loan Mix" subtitle="As of April 2026">
				content
			</ChartCard>,
		);
		expect(screen.getByText("As of April 2026")).toBeInTheDocument();
	});

	it("does not render subtitle element when omitted", () => {
		render(<ChartCard title="Loan Mix">content</ChartCard>);
		expect(screen.queryByRole("paragraph")).toBeNull();
	});

	it("renders children in the body slot", () => {
		render(
			<ChartCard title="Loan Mix">
				<span>chart body</span>
			</ChartCard>,
		);
		expect(screen.getByText("chart body")).toBeInTheDocument();
	});

	it("renders actions slot when provided", () => {
		render(
			<ChartCard
				title="Loan Mix"
				actions={<button type="button">Export</button>}
			>
				content
			</ChartCard>,
		);
		expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
	});

	it("renders footer slot when provided", () => {
		render(
			<ChartCard title="Loan Mix" footer="Source: Origence LOS">
				content
			</ChartCard>,
		);
		expect(screen.getByText("Source: Origence LOS")).toBeInTheDocument();
	});

	it("shows loading skeleton and hides content when loading=true", () => {
		render(
			<ChartCard title="Loan Mix" loading>
				<span>chart body</span>
			</ChartCard>,
		);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByText("Loan Mix")).toBeNull();
		expect(screen.queryByText("chart body")).toBeNull();
	});
});
