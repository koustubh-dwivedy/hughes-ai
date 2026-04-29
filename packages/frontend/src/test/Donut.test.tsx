import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Donut from "../charts/Donut";

const data = [
	{ label: "Current", value: 820 },
	{ label: "Past Due", value: 43 },
	{ label: "Charged Off", value: 12 },
];

describe("Donut", () => {
	it("renders without crashing", () => {
		render(<Donut data={data} />);
	});

	it("shows title when provided", () => {
		render(<Donut data={data} title="Loan Mix" />);
		expect(screen.getByText("Loan Mix")).toBeInTheDocument();
	});

	it("does not render title element when omitted", () => {
		render(<Donut data={data} />);
		expect(screen.queryByRole("figure")).toBeInTheDocument();
		expect(screen.queryByRole("term")).toBeNull();
	});

	it("shows loading placeholder and hides figure when loading=true", () => {
		render(<Donut data={data} loading={true} title="Loan Mix" />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("figure")).toBeNull();
	});

	it("renders a legend entry for each slice label", () => {
		render(<Donut data={data} />);
		for (const slice of data) {
			expect(screen.getByText(slice.label)).toBeInTheDocument();
		}
	});

	it("shows center label when provided", () => {
		render(<Donut data={data} centerLabel="$875M" />);
		expect(screen.getByText("$875M")).toBeInTheDocument();
	});

	it("does not show center label when omitted", () => {
		render(<Donut data={data} />);
		expect(screen.queryByText("$875M")).toBeNull();
	});
});
