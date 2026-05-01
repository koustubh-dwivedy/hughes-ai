import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Chat from "../features/chat";

vi.mock("../shared/api/api", () => ({
	postAsk: vi.fn(),
	getHistory: vi.fn(() => Promise.resolve([])),
	getTrust: vi.fn(() => Promise.resolve({ model: "test", grounding: [] })),
}));

describe("Chat", () => {
	it("renders the ask input and heading", () => {
		render(<Chat />);
		expect(screen.getByText("Hughes AI")).toBeInTheDocument();
		expect(screen.getByRole("textbox")).toBeInTheDocument();
	});
});
