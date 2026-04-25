import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import HistoryPanel from "../components/HistoryPanel";

vi.mock("../lib/api", () => ({
	getHistory: vi.fn(),
	getHistoryDetail: vi.fn(),
	historyDetailToAskResponse: vi.fn((d) => d),
	postRerun: vi.fn(),
}));

vi.mock("../lib/logger", () => ({
	default: { warn: vi.fn(), error: vi.fn() },
}));

import * as api from "../lib/api";

const ITEMS = [
	{
		id: "id-1",
		question: "how many loans",
		sql: "SELECT 1",
		created_at: "2026-04-24T10:00:00Z",
	},
	{
		id: "id-2",
		question: "approval rate",
		sql: "SELECT 2",
		created_at: "2026-04-24T09:00:00Z",
	},
];

afterEach(() => vi.clearAllMocks());

describe("HistoryPanel", () => {
	it("renders nothing while history is empty", async () => {
		vi.mocked(api.getHistory).mockResolvedValue([]);
		const { container } = render(
			<HistoryPanel onSelect={vi.fn()} refreshKey={0} />,
		);
		await waitFor(() => expect(api.getHistory).toHaveBeenCalled());
		expect(container.firstChild).toBeNull();
	});

	it("renders history items after fetch", async () => {
		vi.mocked(api.getHistory).mockResolvedValue(ITEMS);
		render(<HistoryPanel onSelect={vi.fn()} refreshKey={0} />);
		expect(await screen.findByText("how many loans")).toBeInTheDocument();
		expect(screen.getByText("approval rate")).toBeInTheDocument();
	});

	it("calls onSelect with detail when item is clicked", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		vi.mocked(api.getHistory).mockResolvedValue(ITEMS);
		vi.mocked(api.getHistoryDetail).mockResolvedValue(ITEMS[0] as never);
		render(<HistoryPanel onSelect={onSelect} refreshKey={0} />);
		await screen.findByText("how many loans");
		await user.click(screen.getByRole("button", { name: "how many loans" }));
		await waitFor(() => expect(onSelect).toHaveBeenCalledOnce());
	});

	it("calls onSelect after rerun", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		const rerunResult = { ...ITEMS[0], rows: [], columns: [] };
		vi.mocked(api.getHistory).mockResolvedValue(ITEMS);
		vi.mocked(api.postRerun).mockResolvedValue(rerunResult as never);
		render(<HistoryPanel onSelect={onSelect} refreshKey={0} />);
		await screen.findByText("how many loans");
		await user.click(screen.getAllByRole("button", { name: "Rerun" })[0]);
		await waitFor(() => expect(onSelect).toHaveBeenCalledWith(rerunResult));
	});

	it("logs warn and does not crash on fetch failure", async () => {
		const { warn } = await import("../lib/logger").then((m) => m.default);
		vi.mocked(api.getHistory).mockRejectedValue(new Error("network error"));
		render(<HistoryPanel onSelect={vi.fn()} refreshKey={0} />);
		await waitFor(() => expect(warn).toHaveBeenCalled());
	});
});
