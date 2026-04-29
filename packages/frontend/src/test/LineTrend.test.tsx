import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LineTrend from "../charts/LineTrend";

const data = [
	{ period: "Jan-24", value: 2.1 },
	{ period: "Feb-24", value: 2.3 },
	{ period: "Mar-24", value: 2.0 },
	{ period: "Apr-24", value: 2.4 },
];

describe("LineTrend", () => {
	it("renders without crashing", () => {
		render(<LineTrend data={data} />);
	});

	it("shows title when provided", () => {
		render(<LineTrend data={data} title="Delinquency Rate Trend" />);
		expect(screen.getByText("Delinquency Rate Trend")).toBeInTheDocument();
	});

	it("shows loading placeholder and hides figure when loading=true", () => {
		render(<LineTrend data={data} loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("figure")).toBeNull();
	});

	it("uses default series label when none provided", () => {
		render(<LineTrend data={data} />);
		expect(screen.getByText("Value")).toBeInTheDocument();
	});

	it("shows custom seriesLabel in legend", () => {
		render(<LineTrend data={data} seriesLabel="Delinquency Rate (%)" />);
		expect(screen.getByText("Delinquency Rate (%)")).toBeInTheDocument();
	});

	it("renders the figure landmark", () => {
		render(<LineTrend data={data} title="My Chart" />);
		expect(
			screen.getByRole("figure", { name: "My Chart" }),
		).toBeInTheDocument();
	});
});
