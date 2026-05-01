import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import KpiTile from "./KpiTile";

const sparklineData = Array.from({ length: 24 }, (_, i) => ({ value: i * 2 }));

describe("KpiTile v2", () => {
	it("renders label and value", () => {
		render(<KpiTile label="Total Loans" value="$42.5M" />);
		expect(screen.getByText("Total Loans")).toBeInTheDocument();
		expect(screen.getByText("$42.5M")).toBeInTheDocument();
	});

	it("applies green color when deltaPositive=true", () => {
		render(
			<KpiTile
				label="Growth"
				value="$42.5M"
				delta="↑ 4.2%"
				deltaPositive={true}
			/>,
		);
		const deltaEl = screen.getByText("↑ 4.2%");
		expect(deltaEl).toBeInTheDocument();
		expect(deltaEl).toHaveStyle({ color: "#16a34a" });
	});

	it("applies red color when deltaPositive=false", () => {
		render(
			<KpiTile
				label="Loss"
				value="$40M"
				delta="↓ 1.8%"
				deltaPositive={false}
			/>,
		);
		const deltaEl = screen.getByText("↓ 1.8%");
		expect(deltaEl).toBeInTheDocument();
		expect(deltaEl).toHaveStyle({ color: "#dc2626" });
	});

	it("renders skeleton with aria-label=loading when loading=true", () => {
		render(<KpiTile label="Total Loans" value="$42.5M" loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByText("$42.5M")).toBeNull();
	});

	it("fires onClick when tile is clicked", async () => {
		const handleClick = vi.fn();
		render(<KpiTile label="Clickable" value="$10M" onClick={handleClick} />);
		const tile = screen.getByRole("button");
		await userEvent.click(tile);
		expect(handleClick).toHaveBeenCalledTimes(1);
	});

	it("fires onClick when Enter key is pressed", async () => {
		const handleClick = vi.fn();
		render(<KpiTile label="Clickable" value="$10M" onClick={handleClick} />);
		const tile = screen.getByRole("button");
		tile.focus();
		await userEvent.keyboard("{Enter}");
		expect(handleClick).toHaveBeenCalledTimes(1);
	});

	it("renders SVG line element when sparkline data is provided", () => {
		const { container } = render(
			<KpiTile label="Trend" value="$42.5M" sparkline={sparklineData} />,
		);
		const lines = container.querySelectorAll("line, path");
		expect(lines.length).toBeGreaterThan(0);
	});

	it("renders info tooltip button when infoTooltip prop is provided", () => {
		render(
			<KpiTile
				label="Total Loans"
				value="$42.5M"
				infoTooltip="This is the total loan balance"
			/>,
		);
		expect(
			screen.getByRole("button", { name: /This is the total loan balance/i }),
		).toBeInTheDocument();
	});
});
