import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
	renderWithProviders as render,
	screen,
} from "../../../test/test-utils";
import KpiTile from "./KpiTile";

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

	it("renders the info marker with the tooltip text exposed via aria-label", () => {
		render(
			<KpiTile
				label="Total Loans"
				value="$42.5M"
				infoTooltip="This is the total loan balance"
			/>,
		);
		expect(
			screen.getByLabelText("This is the total loan balance"),
		).toBeInTheDocument();
	});

	it("renders deltaLabel and context when supplied", () => {
		render(
			<KpiTile
				label="Total Loans"
				value="$42.5M"
				delta="↑ $1.4M"
				deltaLabel="MoM"
				deltaPositive
				context="Fastest growth in 6 months"
			/>,
		);
		expect(screen.getByText("MoM")).toBeInTheDocument();
		expect(screen.getByText("Fastest growth in 6 months")).toBeInTheDocument();
	});
});
