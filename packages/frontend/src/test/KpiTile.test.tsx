import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KpiTile from "../charts/KpiTile";

describe("KpiTile", () => {
	it("renders label and value", () => {
		render(<KpiTile label="Total Balance" value="$42.5M" />);
		expect(screen.getByText("Total Balance")).toBeInTheDocument();
		expect(screen.getByText("$42.5M")).toBeInTheDocument();
	});

	it("renders numeric value", () => {
		render(<KpiTile label="Count" value={42} />);
		expect(screen.getByText("42")).toBeInTheDocument();
	});

	it("shows up arrow and deltaLabel for positive delta", () => {
		render(
			<KpiTile label="Balance" value="$42M" delta={2.3} deltaLabel="+$2.3M" />,
		);
		expect(screen.getByText(/↑/)).toBeInTheDocument();
		expect(screen.getByText(/\+\$2\.3M/)).toBeInTheDocument();
	});

	it("shows down arrow for negative delta", () => {
		render(
			<KpiTile label="Balance" value="$40M" delta={-1.5} deltaLabel="-$1.5M" />,
		);
		expect(screen.getByText(/↓/)).toBeInTheDocument();
		expect(screen.getByText(/-\$1\.5M/)).toBeInTheDocument();
	});

	it("shows em dash for zero delta", () => {
		render(<KpiTile label="Balance" value="$42M" delta={0} />);
		expect(screen.getByText(/—/)).toBeInTheDocument();
	});

	it("does not render delta row when delta is undefined", () => {
		render(<KpiTile label="Balance" value="$42M" />);
		expect(screen.queryByText(/↑/)).toBeNull();
		expect(screen.queryByText(/↓/)).toBeNull();
		expect(screen.queryByText(/—/)).toBeNull();
	});

	it("shows loading placeholder when loading=true", () => {
		render(<KpiTile label="Balance" value="$42M" loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByText("$42M")).toBeNull();
	});

	it("falls back to absolute delta value when deltaLabel omitted", () => {
		render(<KpiTile label="X" value="10" delta={5} />);
		expect(screen.getByText(/5/)).toBeInTheDocument();
	});
});
