import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import CaseFile from "../features/dispute-cases/CaseFile";
import { renderWithProviders } from "./test-utils";

function renderCase(id: string) {
	return renderWithProviders(
		<MemoryRouter initialEntries={[`/disputes/${id}`]}>
			<Routes>
				<Route path="/disputes/:caseId" element={<CaseFile />} />
			</Routes>
		</MemoryRouter>,
	);
}

describe("CaseFile", () => {
	it("renders a VOD stepper and assembles the debt-verification cover letter", async () => {
		renderCase("CBD-4821");
		// VOD stage rail is present (renamed: Assemble verification).
		expect(
			screen.getByRole("button", { name: /Assemble verification/ }),
		).toBeInTheDocument();
		// Generate the cover-letter preview.
		await userEvent.click(
			screen.getByRole("button", { name: "Generate cover letter" }),
		);
		expect(
			screen.getByRole("dialog", { name: "Validation letter preview" }),
		).toBeInTheDocument();
		expect(
			screen.getByText(/communication from a debt collector/i),
		).toBeInTheDocument();
	});

	it("renders the Fraud stepper with the triangulation matrix", async () => {
		renderCase("CBD-4822");
		// Open the Triangulate ID stage, then assert real vendor names appear.
		await userEvent.click(
			screen.getByRole("button", { name: /Triangulate ID/ }),
		);
		expect(screen.getByText("LexisNexis InstantID")).toBeInTheDocument();
		expect(screen.getByText("Prove")).toBeInTheDocument();
	});

	it("shows a not-found message for an unknown case", () => {
		renderCase("CBD-0000");
		expect(
			screen.getByRole("heading", { name: "Case not found" }),
		).toBeInTheDocument();
	});
});
