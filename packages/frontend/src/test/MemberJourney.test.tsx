import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import MemberJourney from "../features/dispute-cases/member/MemberJourney";
import { renderWithProviders } from "./test-utils";

function renderJourney(memberNumber: string) {
	return renderWithProviders(
		<MemoryRouter initialEntries={[`/disputes/member/${memberNumber}`]}>
			<Routes>
				<Route
					path="/disputes/member/:memberNumber"
					element={<MemberJourney />}
				/>
				<Route path="/disputes" element={<div>Case Queue page</div>} />
			</Routes>
		</MemoryRouter>,
	);
}

function timeline() {
	return screen.getByRole("list");
}

describe("MemberJourney", () => {
	it("renders a rich multi-year timeline with a tiered complaint", () => {
		renderJourney("100558");
		expect(
			screen.getByRole("heading", { name: "Aisha Bello" }),
		).toBeInTheDocument();
		// Escalated T3 complaint surfaces for research.
		expect(screen.getByText("T3 complaint")).toBeInTheDocument();
		expect(screen.getByText(/IVR authentication FAILED/)).toBeInTheDocument();
		// The journey is rich (signature events + generated routine activity).
		expect(within(timeline()).getAllByRole("listitem").length).toBeGreaterThan(
			20,
		);
	});

	it("has a left-aligned back link to the case queue", () => {
		renderJourney("100558");
		expect(
			screen.getByRole("link", { name: /Back to Case Queue/ }),
		).toHaveAttribute("href", "/disputes");
	});

	it("filters the timeline by free-text search", async () => {
		renderJourney("100558");
		const before = within(timeline()).getAllByRole("listitem").length;
		await userEvent.type(
			screen.getByRole("textbox", { name: "Search touchpoints" }),
			"CFPB",
		);
		const after = within(timeline()).getAllByRole("listitem").length;
		expect(after).toBeLessThan(before);
		expect(screen.getByText(/CFPB complaint filed/)).toBeInTheDocument();
	});

	it("filters by category chip", async () => {
		renderJourney("100558");
		await userEvent.click(screen.getByRole("button", { name: "Money" }));
		// Complaints are hidden when the Money category is active.
		expect(screen.queryByText("T3 complaint")).not.toBeInTheDocument();
		// Money-movement touchpoints remain (generated filler includes fees/cards).
		expect(within(timeline()).getAllByRole("listitem").length).toBeGreaterThan(
			0,
		);
	});

	it("narrows the timeline with a From date filter", async () => {
		renderJourney("100558");
		const before = within(timeline()).getAllByRole("listitem").length;
		// Only keep touchpoints on/after 2026-06-01.
		const from = screen.getByLabelText("From date");
		fireEvent.change(from, { target: { value: "2026-06-01" } });
		const after = within(timeline()).getAllByRole("listitem").length;
		expect(after).toBeLessThan(before);
		// Clear restores the full timeline.
		await userEvent.click(screen.getByRole("button", { name: "Clear" }));
		expect(within(timeline()).getAllByRole("listitem").length).toBe(before);
	});

	it("opens a file asset in a blurred overlay and closes it", async () => {
		renderJourney("100558");
		// The CFPB complaint touchpoint carries a mockable file asset.
		await userEvent.click(
			screen.getByRole("button", { name: /CFPB case #26-558201/ }),
		);
		const dialog = screen.getByRole("dialog", {
			name: /CFPB case #26-558201 preview/,
		});
		expect(
			within(dialog).getByText(/Consumer Financial Protection Bureau/),
		).toBeInTheDocument();
		// Rendered as a clean scanned page with a received annotation.
		expect(within(dialog).getByTestId("scanned-document")).toBeInTheDocument();
		expect(within(dialog).getByText(/Received/)).toBeInTheDocument();
		await userEvent.click(
			within(dialog).getByRole("button", { name: "Close" }),
		);
		expect(
			screen.queryByRole("dialog", { name: /CFPB case #26-558201 preview/ }),
		).not.toBeInTheDocument();
	});

	it("falls back gracefully for an unknown member", () => {
		renderJourney("999999");
		expect(
			screen.getByRole("heading", { name: "Member 999999" }),
		).toBeInTheDocument();
	});
});
