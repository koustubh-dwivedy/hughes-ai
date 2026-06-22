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
			</Routes>
		</MemoryRouter>,
	);
}

function renderQueue() {
	return renderWithProviders(
		<MemoryRouter initialEntries={["/disputes"]}>
			<Routes>
				<Route path="/disputes" element={<DisputeQueue />} />
			</Routes>
		</MemoryRouter>,
	);
}

/** Clicks Continue across stages until the case can be (and is) resolved. */
async function advanceToResolve() {
	for (let guard = 0; guard < 12; guard++) {
		const resolveBtn = screen.queryByRole("button", { name: /Resolve case/ });
		if (resolveBtn && !(resolveBtn as HTMLButtonElement).disabled) {
			await userEvent.click(resolveBtn);
			return;
		}
		const cont = screen.queryByRole("button", {
			name: /Complete step & continue/,
		});
		if (cont && !(cont as HTMLButtonElement).disabled) {
			await userEvent.click(cont);
		} else {
			return;
		}
	}
}

describe("case step-through to completion", () => {
	it("gates advancing past Decide until a disposition is recorded", async () => {
		renderCase("CBD-4822"); // lands on the Decide stage (active)
		expect(
			screen.getByRole("button", { name: /Complete step & continue/ }),
		).toBeDisabled();
		// Record a decision on Triangulate, then return to the active Decide step.
		await userEvent.click(screen.getByRole("button", { name: /Triangulate ID/ }));
		await userEvent.click(screen.getByRole("button", { name: "Approve" }));
		await userEvent.click(screen.getByRole("button", { name: /Decide/ }));
		expect(
			screen.getByRole("button", { name: /Complete step & continue/ }),
		).toBeEnabled();
	});

	it("advances and resolves the case, showing a completion banner", async () => {
		renderCase("CBD-4822");
		await userEvent.click(screen.getByRole("button", { name: /Triangulate ID/ }));
		await userEvent.click(screen.getByRole("button", { name: "Approve" }));
		await userEvent.click(screen.getByRole("button", { name: /Decide/ }));
		await advanceToResolve();
		expect(
			screen.getByText(/Case resolved — Blocked & suppressed/),
		).toBeInTheDocument();
	});

	it("reflects a resolved case in the queue status (session store)", async () => {
		const { unmount } = renderCase("CBD-4821"); // VOD, no decision gate
		await advanceToResolve();
		expect(screen.getByText(/Case resolved — /)).toBeInTheDocument();
		unmount();

		renderQueue();
		const row = within(screen.getByRole("table"))
			.getByText("CBD-4821")
			.closest("tr");
		expect(row).not.toBeNull();
		if (row) {
			expect(within(row).getByText("Resolved")).toBeInTheDocument();
		}
	});
});
