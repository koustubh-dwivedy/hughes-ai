import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Launchpad from "../features/launchpad/Launchpad";
import { renderWithProviders } from "./test-utils";

function renderLaunchpad() {
	return renderWithProviders(
		<MemoryRouter initialEntries={["/"]}>
			<Routes>
				<Route path="/" element={<Launchpad />} />
				<Route path="/disputes" element={<div>Dispute Center page</div>} />
			</Routes>
		</MemoryRouter>,
	);
}

describe("Launchpad", () => {
	it("renders exactly the two live product tiles", () => {
		renderLaunchpad();
		expect(screen.getByText("Business Intelligence")).toBeInTheDocument();
		expect(screen.getByText("Dispute Center")).toBeInTheDocument();
		// No "Lending Intelligence" (renamed) and no coming-soon tiles.
		expect(screen.queryByText("Lending Intelligence")).not.toBeInTheDocument();
		expect(screen.queryByText("Coming soon")).not.toBeInTheDocument();
	});

	it("navigates into a live product when its tile is clicked", async () => {
		renderLaunchpad();
		await userEvent.click(screen.getByTestId("product-dispute-center"));
		expect(screen.getByText("Dispute Center page")).toBeInTheDocument();
	});
});
