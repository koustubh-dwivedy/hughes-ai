import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AskResponse } from "../../shared/api/api";
import { formatDayLabel } from "./DaySeparator";
import Thread, { type ThreadMessage } from "./Thread";

const ASSISTANT_RESULT: AskResponse = {
	request_id: "r1",
	question: "Q",
	sql: "select 1",
	explanation: "Forty-two loans.",
	tables_used: [],
	assumptions: [],
	caveats: [],
	rows: [],
	columns: [],
	clarification: null,
};

function ts(year: number, month: number, day: number, hour = 12): number {
	return Date.UTC(year, month - 1, day, hour);
}

describe("Thread", () => {
	it("renders user and assistant cards in submission order", () => {
		const messages: ThreadMessage[] = [
			{ id: "u1", kind: "user", question: "Q1", timestamp: ts(2026, 5, 1) },
			{
				id: "a1",
				kind: "assistant",
				result: ASSISTANT_RESULT,
				timestamp: ts(2026, 5, 1, 13),
			},
			{ id: "u2", kind: "user", question: "Q2", timestamp: ts(2026, 5, 1, 14) },
		];
		render(<Thread messages={messages} />);
		expect(screen.getByText("Q1")).toBeInTheDocument();
		expect(screen.getByText("Forty-two loans.")).toBeInTheDocument();
		expect(screen.getByText("Q2")).toBeInTheDocument();
	});

	it("renders three user questions all visible (HUG-132 acceptance)", () => {
		const messages: ThreadMessage[] = [
			{ id: "u1", kind: "user", question: "First", timestamp: ts(2026, 5, 1) },
			{
				id: "u2",
				kind: "user",
				question: "Second",
				timestamp: ts(2026, 5, 1, 13),
			},
			{
				id: "u3",
				kind: "user",
				question: "Third",
				timestamp: ts(2026, 5, 1, 14),
			},
		];
		render(<Thread messages={messages} />);
		expect(screen.getByText("First")).toBeInTheDocument();
		expect(screen.getByText("Second")).toBeInTheDocument();
		expect(screen.getByText("Third")).toBeInTheDocument();
	});

	it("inserts day separator only when day changes", () => {
		const messages: ThreadMessage[] = [
			{ id: "u1", kind: "user", question: "Q1", timestamp: ts(2026, 4, 30) },
			{
				id: "u2",
				kind: "user",
				question: "Q2",
				timestamp: ts(2026, 4, 30, 18),
			},
			{ id: "u3", kind: "user", question: "Q3", timestamp: ts(2026, 5, 1) },
		];
		render(<Thread messages={messages} />);
		expect(screen.getAllByRole("separator")).toHaveLength(2);
	});

	it("renders error messages as role=alert", () => {
		const messages: ThreadMessage[] = [
			{ id: "e1", kind: "error", message: "Boom", timestamp: ts(2026, 5, 1) },
		];
		render(<Thread messages={messages} />);
		expect(screen.getByRole("alert")).toHaveTextContent("Boom");
	});

	it("uses role=log with aria-live=polite for screen readers", () => {
		render(<Thread messages={[]} />);
		const log = screen.getByRole("log");
		expect(log).toHaveAttribute("aria-live", "polite");
	});
});

describe("formatDayLabel", () => {
	const today = new Date("2026-05-02T12:00:00Z");

	it("returns Today for today's date", () => {
		expect(formatDayLabel("2026-05-02", today)).toBe("Today");
	});

	it("returns Yesterday for yesterday", () => {
		expect(formatDayLabel("2026-05-01", today)).toBe("Yesterday");
	});

	it("returns short date for older dates in same year", () => {
		const result = formatDayLabel("2026-04-15", today);
		expect(result).toMatch(/Apr/);
		expect(result).not.toMatch(/2026/);
	});

	it("includes year for dates in other years", () => {
		const result = formatDayLabel("2025-12-15", today);
		expect(result).toMatch(/2025/);
	});
});
