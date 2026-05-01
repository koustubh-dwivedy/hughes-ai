import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DateBadge from "./DateBadge";

describe("DateBadge", () => {
	it("formats 2026-04-30 correctly with Intl", () => {
		render(<DateBadge asOfDate="2026-04-30" />);
		expect(screen.getByRole("status")).toHaveTextContent("As of Apr 30, 2026");
	});

	it("shows refreshed X min ago when refreshedAt is 5 min ago", () => {
		const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
		render(<DateBadge asOfDate="2026-04-30" refreshedAt={fiveMinAgo} />);
		expect(screen.getByRole("status")).toHaveTextContent("refreshed 5 min ago");
	});

	it("shows just now when refreshedAt is 30s ago", () => {
		const thirtySecAgo = new Date(Date.now() - 30 * 1000).toISOString();
		render(<DateBadge asOfDate="2026-04-30" refreshedAt={thirtySecAgo} />);
		expect(screen.getByRole("status")).toHaveTextContent("just now");
	});

	it("has role status", () => {
		render(<DateBadge asOfDate="2026-04-30" />);
		expect(screen.getByRole("status")).toBeInTheDocument();
	});

	it("tooltip prop sets title attribute", () => {
		render(
			<DateBadge
				asOfDate="2026-04-30"
				tooltip="Data is updated nightly at midnight"
			/>,
		);
		expect(screen.getByRole("status")).toHaveAttribute(
			"title",
			"Data is updated nightly at midnight",
		);
	});
});
