import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import DisputeQueue from "../features/dispute-cases/DisputeQueue";
import { renderWithProviders } from "./test-utils";

function renderQueue() {
	return renderWithProviders(
		<MemoryRouter initialEntries={["/disputes"]}>
			<Routes>
				<Route path="/disputes" element={<DisputeQueue />} />
				<Route path="/disputes/:caseId" element={<div>Case file</div>} />
			</Routes>
		</MemoryRouter>,
	);
}

describe("DisputeQueue", () => {
	it("renders the KPI strip and the queue header", () => {
		renderQueue();
		expect(screen.getByText("Open cases")).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Case Queue" }),
		).toBeInTheDocument();
	});

	it("shows Metro 2 columns (CCC, ACDV #)", () => {
		renderQueue();
		expect(screen.getByText("CCC")).toBeInTheDocument();
		expect(screen.getByText("ACDV #")).toBeInTheDocument();
	});

	it("filters the queue by type", async () => {
		renderQueue();
		const table = screen.getByRole("table");
		// Both types visible under "All".
		expect(within(table).getByText("CBD-5101")).toBeInTheDocument();
		expect(within(table).getByText("CBD-4822")).toBeInTheDocument();
		await userEvent.click(screen.getByRole("button", { name: "Fraud" }));
		expect(within(table).queryByText("CBD-5101")).not.toBeInTheDocument();
		expect(within(table).getByText("CBD-4822")).toBeInTheDocument();
	});

	it("navigates to a case file when a row is clicked", async () => {
		renderQueue();
		await userEvent.click(screen.getByText("CBD-5101"));
		expect(screen.getByText("Case file")).toBeInTheDocument();
	});
});
