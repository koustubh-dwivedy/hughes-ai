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
	it("renders a data-accuracy stepper with the field-comparison journey", async () => {
		renderCase("CBD-5101");
		// The ACDV data-accuracy stage rail is present.
		expect(
			screen.getByRole("button", { name: /Compare fields/ }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /Decide response/ }),
		).toBeInTheDocument();
		// The header carries the reason code and the eOSCAR channel context.
		expect(screen.getByText(/Reason 118/)).toBeInTheDocument();
	});

	it("renders the Fraud stepper with the triangulation matrix", async () => {
		renderCase("CBD-4822");
		// Open the merged Triangulate & decide stage; assert real vendor names.
		await userEvent.click(
			screen.getByRole("button", { name: /Triangulate & decide/ }),
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
