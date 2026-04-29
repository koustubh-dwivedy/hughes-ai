import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Combo from "../charts/Combo";

const data = [
	{ period: "Jan-24", bar: 42.5, line: 6.8 },
	{ period: "Feb-24", bar: 43.1, line: 6.9 },
	{ period: "Mar-24", bar: 41.8, line: 6.7 },
];

describe("Combo", () => {
	it("renders without crashing", () => {
		render(<Combo data={data} />);
	});

	it("shows title when provided", () => {
		render(<Combo data={data} title="Balance vs. Rate" />);
		expect(screen.getByText("Balance vs. Rate")).toBeInTheDocument();
	});

	it("shows loading placeholder and hides figure when loading=true", () => {
		render(<Combo data={data} loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("figure")).toBeNull();
	});

	it("uses default labels when none provided", () => {
		render(<Combo data={data} />);
		expect(screen.getByText("Bar")).toBeInTheDocument();
		expect(screen.getByText("Line")).toBeInTheDocument();
	});

	it("shows custom barLabel in legend", () => {
		render(<Combo data={data} barLabel="Loan Balance ($M)" />);
		expect(screen.getByText("Loan Balance ($M)")).toBeInTheDocument();
	});

	it("shows custom lineLabel in legend", () => {
		render(<Combo data={data} lineLabel="Avg Rate (%)" />);
		expect(screen.getByText("Avg Rate (%)")).toBeInTheDocument();
	});

	it("renders both bar and line entries in legend", () => {
		render(<Combo data={data} barLabel="Balance" lineLabel="Rate" />);
		expect(screen.getByText("Balance")).toBeInTheDocument();
		expect(screen.getByText("Rate")).toBeInTheDocument();
	});
});
