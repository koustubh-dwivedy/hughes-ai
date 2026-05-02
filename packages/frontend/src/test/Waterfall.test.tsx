import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Waterfall from "../charts/Waterfall";

const data = [
	{ label: "Start", value: 100, isTotal: true as const },
	{ label: "New Loans", value: 50 },
	{ label: "Payoffs", value: -30 },
	{ label: "Charged Off", value: 0 },
	{ label: "End", value: 120, isTotal: true as const },
];

describe("Waterfall", () => {
	it("renders without crashing with positive, negative, and zero steps", () => {
		render(<Waterfall data={data} />);
	});

	it("shows title when provided", () => {
		render(<Waterfall data={data} title="Loan Balance Waterfall" />);
		expect(screen.getByText("Loan Balance Waterfall")).toBeInTheDocument();
	});

	it("shows loading placeholder and hides figure when loading=true", () => {
		render(<Waterfall data={data} loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("figure")).toBeNull();
	});

	it("renders XAxis label for each step", () => {
		const { container } = render(<Waterfall data={data} />);
		// SVG <tspan> wrapping makes screen.getByText brittle and may
		// strip inter-word spaces in textContent; compare with whitespace
		// removed so multi-word labels still match.
		const txt = (container.textContent ?? "").replace(/\s+/g, "");
		for (const step of data) {
			expect(txt).toContain(step.label.replace(/\s+/g, ""));
		}
	});

	it("renders with only positive steps", () => {
		const { container } = render(
			<Waterfall
				data={[
					{ label: "Base", value: 10, isTotal: true },
					{ label: "Up", value: 5 },
				]}
			/>,
		);
		const txt = container.textContent ?? "";
		expect(txt).toContain("Base");
		expect(txt).toContain("Up");
	});

	it("renders with only negative steps", () => {
		render(
			<Waterfall
				data={[
					{ label: "Start", value: 50, isTotal: true },
					{ label: "Loss", value: -20 },
				]}
			/>,
		);
		expect(screen.getByText("Loss")).toBeInTheDocument();
	});
});
