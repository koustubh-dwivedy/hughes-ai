import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Chat from "../features/chat";

vi.mock("../shared/api/api", () => ({
	postAsk: vi.fn(),
	getHistoryDetail: vi.fn(),
	historyDetailToAskResponse: vi.fn(),
	getTrust: vi.fn(() => Promise.resolve({ model: "test", grounding: [] })),
}));

describe("Chat", () => {
	it("renders the ask input and heading", () => {
		render(
			<MemoryRouter>
				<Chat />
			</MemoryRouter>,
		);
		expect(screen.getByText("Hughes AI")).toBeInTheDocument();
		expect(screen.getByRole("textbox")).toBeInTheDocument();
	});
});
