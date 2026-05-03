import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Chat from "../features/chat";
import { renderWithProviders } from "./test-utils";

describe("Chat", () => {
	it("renders the ask input and suggested prompts", () => {
		renderWithProviders(
			<MemoryRouter>
				<Chat />
			</MemoryRouter>,
		);
		expect(screen.getByRole("textbox")).toBeInTheDocument();
	});

	it("does not render a 'Hughes AI' heading inside the chat surface", () => {
		renderWithProviders(
			<MemoryRouter>
				<Chat />
			</MemoryRouter>,
		);
		expect(screen.queryByRole("heading", { name: "Hughes AI" })).toBeNull();
	});

	it("does not render a TrustPanel sidebar inside the chat surface", () => {
		renderWithProviders(
			<MemoryRouter>
				<Chat />
			</MemoryRouter>,
		);
		expect(screen.queryByText(/Data Freshness/)).toBeNull();
	});
});
