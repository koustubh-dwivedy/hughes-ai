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

/** If the current stage has a sign-off gate, pick the first option + add notes. */
async function fillSignoffIfPresent() {
	const notes = screen.queryByLabelText("Sign-off notes");
	if (!notes) return;
	for (const label of ["Approve", "Confirm match", "Confirm AI findings"]) {
		const btn = screen.queryByRole("button", { name: label });
		if (btn) {
			await userEvent.click(btn);
			break;
		}
	}
	await userEvent.type(notes, "Reviewed; concur with AI.");
}

/** Sign off where required, advancing across stages, then resolve. */
async function advanceToResolve() {
	for (let guard = 0; guard < 12; guard++) {
		await fillSignoffIfPresent();
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
	it("blocks advancing past the merged investigate step until an option AND notes are provided", async () => {
		renderCase("CBD-4822"); // lands on the Triangulate & decide sign-off gate
		const cont = () =>
			screen.getByRole("button", { name: /Complete step & continue/ });
		expect(cont()).toBeDisabled();
		// Option alone is not enough.
		await userEvent.click(screen.getByRole("button", { name: "Approve" }));
		expect(cont()).toBeDisabled();
		// Notes complete the sign-off.
		await userEvent.type(
			screen.getByLabelText("Sign-off notes"),
			"Concur with the block.",
		);
		expect(cont()).toBeEnabled();
	});

	it("advances and resolves a fraud case, showing a completion banner", async () => {
		renderCase("CBD-4822");
		await advanceToResolve();
		expect(
			screen.getByText(/Case resolved — Blocked & suppressed/),
		).toBeInTheDocument();
	});

	it("reflects a resolved case in the queue status (session store)", async () => {
		const { unmount } = renderCase("CBD-4821"); // VOD
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
