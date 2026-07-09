import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import CaseFile from "../features/dispute-cases/CaseFile";
import DisputeQueue from "../features/dispute-cases/DisputeQueue";
import { resetCaseProgress } from "../features/dispute-cases/data/caseProgressStore";
import { renderWithProviders } from "./test-utils";

afterEach(() => resetCaseProgress());

function renderCase(id: string) {
	return renderWithProviders(
		<MemoryRouter initialEntries={[`/disputes/${id}`]}>
			<Routes>
				<Route path="/disputes/:caseId" element={<CaseFile />} />
				<Route
					path="/disputes/member/:memberNumber"
					element={<div>Member journey page</div>}
				/>
			</Routes>
		</MemoryRouter>,
	);
}

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

/** Click "Complete step & continue" until the Resolve button is reached + fired. */
async function resolveNoSignoff() {
	for (let guard = 0; guard < 8; guard++) {
		const resolve = screen.queryByRole("button", { name: /Resolve case/ });
		if (resolve && !(resolve as HTMLButtonElement).disabled) {
			await userEvent.click(resolve);
			return;
		}
		const cont = screen.queryByRole("button", {
			name: /Complete step & continue/,
		});
		if (!cont || (cont as HTMLButtonElement).disabled) return;
		await userEvent.click(cont);
	}
}

describe("ACDV data-accuracy track", () => {
	it("auto-resolves an autonomous case (CBD-5101) with no human sign-off", async () => {
		renderCase("CBD-5101");
		// Header shows the data-accuracy type + reason code.
		// Type is the master-table category for the reason code (118 → Account Specific).
		expect(screen.getByText("Account Specific")).toBeInTheDocument();
		expect(screen.getByText(/Reason 118/)).toBeInTheDocument();

		// The case opens on Intake; walk Intake → Compare → Decide.
		const cont = () =>
			screen.getByRole("button", { name: /Complete step & continue/ });
		await userEvent.click(cont()); // Intake → Compare
		await userEvent.click(cont()); // Compare → Decide
		expect(
			screen.getByText(/Auto-resolved — all three gates passed/),
		).toBeInTheDocument();
		expect(screen.queryByLabelText("Sign-off notes")).not.toBeInTheDocument();
		expect(screen.getByText(/21 — Updated disputed field/)).toBeInTheDocument();

		await resolveNoSignoff();
		expect(
			screen.getByText(/Case resolved — Corrected & refurnished/),
		).toBeInTheDocument();
	});

	it("blocks a gated case (CBD-5102) until the image is viewed AND signed off", async () => {
		renderCase("CBD-5102"); // opens on Intake
		const cont = () =>
			screen.getByRole("button", { name: /Complete step & continue/ });
		await userEvent.click(cont()); // Intake → Compare
		await userEvent.click(cont()); // Compare → Decide (image + free-text gate)

		// The consumer image is unviewed and the sign-off gate is present.
		expect(
			screen.getByText(/Action required — not yet viewed/),
		).toBeInTheDocument();
		expect(cont()).toBeDisabled();

		// View the TIFF → acknowledged (mandatory View/Print/Download action).
		await userEvent.click(
			screen.getByRole("button", { name: /Bank statement/ }),
		);
		expect(screen.getByTestId("scanned-document")).toBeInTheDocument();
		await userEvent.click(
			within(screen.getByRole("dialog")).getByRole("button", { name: "Close" }),
		);
		expect(screen.getByText("Viewed")).toBeInTheDocument();

		// Still blocked on the human sign-off.
		expect(cont()).toBeDisabled();
		await userEvent.click(screen.getByRole("button", { name: "Approve" }));
		await userEvent.type(
			screen.getByLabelText("Sign-off notes"),
			"Statement confirms on-time payment; correcting status + balance.",
		);
		expect(cont()).toBeEnabled();
	});

	it("shows the field comparison (as-reported vs system of record) on CBD-5101", async () => {
		renderCase("CBD-5101");
		await userEvent.click(
			screen.getByRole("button", { name: /Compare fields/ }),
		);
		expect(screen.getByText("System of record")).toBeInTheDocument();
		// $8,400 appears in both the summary panel and the comparison; SOR $7,980 is unique.
		expect(screen.getAllByText("$8,400").length).toBeGreaterThan(0);
		expect(screen.getByText("$7,980")).toBeInTheDocument();
	});

	it("shows master-table category filters + columns and never 'Overdue' or 'Unassigned'", () => {
		renderQueue();
		// Filter tabs are the master-table categories present in the data.
		expect(
			screen.getByRole("button", { name: "Account Specific" }),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Fraud" })).toBeInTheDocument();
		expect(screen.getByText("Reason")).toBeInTheDocument();
		expect(screen.getByText("Response")).toBeInTheDocument();
		// No queue row ever reads "Overdue"; no case is Unassigned.
		expect(screen.queryByText("Overdue")).not.toBeInTheDocument();
		expect(screen.queryByText("Unassigned")).not.toBeInTheDocument();
	});

	it("filters the queue by master-table category", async () => {
		renderQueue();
		const table = screen.getByRole("table");
		expect(within(table).getByText("CBD-5101")).toBeInTheDocument();
		expect(within(table).getByText("CBD-4822")).toBeInTheDocument();
		// CBD-5101 is code 118 → "Account Specific"; CBD-4822 is fraud → hidden.
		await userEvent.click(
			screen.getByRole("button", { name: "Account Specific" }),
		);
		expect(within(table).getByText("CBD-5101")).toBeInTheDocument();
		expect(within(table).queryByText("CBD-4822")).not.toBeInTheDocument();
	});
});
