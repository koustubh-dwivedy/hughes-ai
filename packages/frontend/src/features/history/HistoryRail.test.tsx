import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { renderWithProviders } from "../../test/test-utils";
import HistoryRail, { dayLabel, groupByDay } from "./HistoryRail";

const ITEMS: api.HistorySummary[] = [
	{
		id: "id-1",
		question: "What is the past-due ratio?",
		sql: "SELECT 1",
		created_at: "2026-05-02T13:00:00Z",
	},
	{
		id: "id-2",
		question: "How many active loans?",
		sql: "SELECT 2",
		created_at: "2026-05-02T09:30:00Z",
	},
	{
		id: "id-3",
		question: "Top branches by deposits",
		sql: "SELECT 3",
		created_at: "2026-05-01T14:00:00Z",
	},
	{
		id: "id-4",
		question: "Officer with highest delinquency",
		sql: "SELECT 4",
		created_at: "2026-04-28T10:00:00Z",
	},
];

afterEach(() => {
	vi.restoreAllMocks();
});

function renderRail() {
	return renderWithProviders(
		<MemoryRouter>
			<HistoryRail onSelect={vi.fn()} />
		</MemoryRouter>,
	);
}

describe("dayLabel", () => {
	const today = new Date("2026-05-02T12:00:00Z");
	it("returns Today for today", () => {
		expect(dayLabel("2026-05-02", today)).toBe("Today");
	});
	it("returns Yesterday for yesterday", () => {
		expect(dayLabel("2026-05-01", today)).toBe("Yesterday");
	});
	it("returns short label for older same-year date", () => {
		expect(dayLabel("2026-04-28", today)).toMatch(/Apr/);
	});
});

describe("groupByDay", () => {
	it("groups items by date and sorts groups newest-first", () => {
		const groups = groupByDay(ITEMS);
		expect(groups.map((g) => g.dateKey)).toEqual([
			"2026-05-02",
			"2026-05-01",
			"2026-04-28",
		]);
		expect(groups[0]?.items).toHaveLength(2);
	});
});

describe("HistoryRail", () => {
	it("renders day headers and items grouped by day", async () => {
		vi.spyOn(api, "getHistory").mockResolvedValue(ITEMS);
		renderRail();
		await waitFor(() => {
			expect(
				screen.getByText("What is the past-due ratio?"),
			).toBeInTheDocument();
		});
		expect(
			screen.getByRole("heading", { name: "Today", level: 3 }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Yesterday", level: 3 }),
		).toBeInTheDocument();
	});

	it("filters items via the search box", async () => {
		vi.spyOn(api, "getHistory").mockResolvedValue(ITEMS);
		renderRail();
		await waitFor(() => {
			expect(screen.getByText("Top branches by deposits")).toBeInTheDocument();
		});
		fireEvent.change(screen.getByLabelText("Search history"), {
			target: { value: "branches" },
		});
		expect(screen.getByText("Top branches by deposits")).toBeInTheDocument();
		expect(screen.queryByText("How many active loans?")).toBeNull();
	});

	it("shows empty state when no history exists", async () => {
		vi.spyOn(api, "getHistory").mockResolvedValue([]);
		renderRail();
		await waitFor(() => {
			expect(screen.getByText("No history yet.")).toBeInTheDocument();
		});
	});

	it("calls onSelect with item id when clicked", async () => {
		vi.spyOn(api, "getHistory").mockResolvedValue(ITEMS);
		const onSelect = vi.fn();
		renderWithProviders(
			<MemoryRouter>
				<HistoryRail onSelect={onSelect} />
			</MemoryRouter>,
		);
		await waitFor(() => {
			expect(
				screen.getByText("What is the past-due ratio?"),
			).toBeInTheDocument();
		});
		fireEvent.click(screen.getByText("What is the past-due ratio?"));
		expect(onSelect).toHaveBeenCalledWith("id-1");
	});
});
