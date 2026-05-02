import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Chat from "../features/chat";
import { renderWithProviders } from "./test-utils";

describe("Chat", () => {
	it("renders the ask input and heading", () => {
		renderWithProviders(
			<MemoryRouter>
				<Chat />
			</MemoryRouter>,
		);
		expect(screen.getByText("Hughes AI")).toBeInTheDocument();
		expect(screen.getByRole("textbox")).toBeInTheDocument();
	});
});
