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
				<Route
					path="/disputes/member/:memberNumber"
					element={<div>Member journey page</div>}
				/>
			</Routes>
		</MemoryRouter>,
	);
}

describe("AI human-in-the-loop layer", () => {
	it("shows the verdict + stance-summary evidence on the fraud Triangulate stage", async () => {
		renderCase("CBD-4822");
		await userEvent.click(
			screen.getByRole("button", { name: /Triangulate & decide/ }),
		);
		expect(screen.getByText("✨ Agentic AI")).toBeInTheDocument();
		expect(screen.getByText("AI recommendation")).toBeInTheDocument();
		// Recommendation appears in the verdict header (and the decision prompt).
		expect(
			screen.getAllByText(/Block tradeline \(§605B\)/).length,
		).toBeGreaterThan(0);
		expect(screen.getByText("Synthesis")).toBeInTheDocument();
		// Stance summary counts: 5 supports / 1 against / 3 inconclusive.
		expect(screen.getByText("Supports fraud 5")).toBeInTheDocument();
		expect(screen.getByText("Argues against 1")).toBeInTheDocument();
		expect(screen.getByText("Inconclusive 3")).toBeInTheDocument();
	});

	it("expands a signal to reveal the agent's resolution + raw datapoints", async () => {
		renderCase("CBD-4822");
		await userEvent.click(
			screen.getByRole("button", { name: /Triangulate & decide/ }),
		);
		await userEvent.click(screen.getByRole("button", { name: /Prove/ }));
		expect(screen.getByText("How AI resolved this")).toBeInTheDocument();
		expect(
			screen.getByText(
				/Possession of the enrollment line could not be confirmed/,
			),
		).toBeInTheDocument();
		// A raw datapoint behind the call.
		expect(screen.getByText("Trust score")).toBeInTheDocument();
	});

	it("offers an info-hover explaining what a validation checks", async () => {
		renderCase("CBD-4822");
		await userEvent.click(
			screen.getByRole("button", { name: /Triangulate & decide/ }),
		);
		expect(
			screen.getByLabelText(/flags recent SIM-swap or porting/),
		).toBeInTheDocument();
	});

	it("expands the agent's reasoning trace (synthesis)", async () => {
		renderCase("CBD-4822");
		await userEvent.click(
			screen.getByRole("button", { name: /Triangulate & decide/ }),
		);
		await userEvent.click(
			screen.getByRole("button", { name: /How AI reasoned/ }),
		);
		expect(screen.getByText(/Synthesize/)).toBeInTheDocument();
	});

	it("shows evidence and the sign-off gate together on the merged Triangulate & decide step", async () => {
		renderCase("CBD-4822"); // lands on the merged stage (active)
		// Evidence (from InvestigationReview) and the gate are on the same step.
		expect(screen.getByText("Supports fraud 5")).toBeInTheDocument();
		expect(screen.getByText(/Human sign-off required/)).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
		expect(screen.getByLabelText("Sign-off notes")).toBeInTheDocument();
	});

	it("shows a recorded human sign-off on a gate the case already cleared", async () => {
		renderCase("CBD-4822"); // intake gate already cleared (case is past it)
		await userEvent.click(screen.getByRole("button", { name: /Intake/ }));
		const notes = screen.getByLabelText(
			"Sign-off notes",
		) as HTMLTextAreaElement;
		expect(notes.value).toMatch(/police report cross-checked/);
	});

	it("shows the AI-extracted intake panel on the fraud Intake stage", async () => {
		renderCase("CBD-4822");
		await userEvent.click(screen.getByRole("button", { name: /Intake/ }));
		expect(screen.getByText("✨ AI-extracted")).toBeInTheDocument();
	});

	it("shows deterministic provenance on the VOD Triage stage", async () => {
		renderCase("CBD-4821");
		await userEvent.click(screen.getByRole("button", { name: /Triage/ }));
		expect(screen.getByText("Deterministic")).toBeInTheDocument();
	});

	it("shows the AI received-vs-system-of-record match on VOD intake", async () => {
		renderCase("CBD-4821");
		await userEvent.click(screen.getByRole("button", { name: /Intake/ }));
		expect(
			screen.getByText(/received vs system of record/i),
		).toBeInTheDocument();
		expect(screen.getByText("Matched to member of record")).toBeInTheDocument();
		// A comparison row (System of record column header).
		expect(screen.getByText("System of record")).toBeInTheDocument();
	});

	it("requires a human sign-off on VOD Close before resolving", async () => {
		renderCase("CBD-4821");
		await userEvent.click(screen.getByRole("button", { name: /^.*Close/ }));
		// The AI validation-QA now gates resolution behind an explicit sign-off.
		expect(screen.getByText(/Human sign-off required/)).toBeInTheDocument();
		expect(screen.getByText(/AI recommends:/)).toBeInTheDocument();
		expect(screen.getByLabelText("Sign-off notes")).toBeInTheDocument();
	});

	it("gates VOD intake behind a human sign-off on the AI identity match", async () => {
		renderCase("CBD-4821");
		await userEvent.click(screen.getByRole("button", { name: /Intake/ }));
		expect(
			screen.getByRole("button", { name: "Confirm match" }),
		).toBeInTheDocument();
		expect(screen.getByLabelText("Sign-off notes")).toBeInTheDocument();
	});

	it("renders the merged Suppress & block (§605B) fraud stage", async () => {
		renderCase("CBD-4822");
		await userEvent.click(
			screen.getByRole("button", { name: /Suppress & block/ }),
		);
		expect(screen.getByText(/§605B clock:/)).toBeInTheDocument();
		expect(screen.getByText(/runs in parallel/)).toBeInTheDocument();
	});

	it("opens the member journey in a new tab from the case file", () => {
		renderCase("CBD-4822");
		const link = screen.getByRole("link", { name: /View customer journey/ });
		expect(link).toHaveAttribute("href", "/disputes/member/100558");
		expect(link).toHaveAttribute("target", "_blank");
		expect(link).toHaveAttribute("rel", "noopener noreferrer");
	});

	it("has a left-aligned back-to-queue link on the case file", () => {
		renderCase("CBD-4822");
		expect(
			screen.getByRole("link", { name: /Back to Case Queue/ }),
		).toBeInTheDocument();
	});
});
