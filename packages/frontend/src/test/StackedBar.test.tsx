import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StackedBar from "../charts/StackedBar";

const data = [
	{ period: "Jan-24", "1-14": 12, "15-29": 8, "30-59": 5 },
	{ period: "Feb-24", "1-14": 10, "15-29": 9, "30-59": 6 },
	{ period: "Mar-24", "1-14": 11, "15-29": 7, "30-59": 4 },
];

const series = [{ key: "1-14" }, { key: "15-29" }, { key: "30-59" }];

describe("StackedBar", () => {
	it("renders without crashing", () => {
		render(<StackedBar data={data} series={series} />);
	});

	it("shows title when provided", () => {
		render(
			<StackedBar data={data} series={series} title="Delinquency Trend" />,
		);
		expect(screen.getByText("Delinquency Trend")).toBeInTheDocument();
	});

	it("shows loading placeholder and hides figure when loading=true", () => {
		render(<StackedBar data={data} series={series} loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("figure")).toBeNull();
	});

	it("renders a legend entry for each series key", () => {
		render(<StackedBar data={data} series={series} />);
		for (const s of series) {
			expect(screen.getByText(s.key)).toBeInTheDocument();
		}
	});

	it("renders correct number of legend entries", () => {
		render(<StackedBar data={data} series={series} />);
		const legendItems = screen
			.getAllByRole("listitem")
			.filter((el) => el.className.includes("recharts"));
		expect(legendItems).toHaveLength(series.length);
	});

	it("accepts custom colors per series", () => {
		const colored = [
			{ key: "1-14", color: "#ff0000" },
			{ key: "15-29", color: "#00ff00" },
		];
		render(<StackedBar data={data} series={colored} />);
		expect(screen.getByText("1-14")).toBeInTheDocument();
		expect(screen.getByText("15-29")).toBeInTheDocument();
	});
});
