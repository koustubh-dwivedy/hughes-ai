import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import TrustPanel from "../features/chat/TrustPanel";
import * as api from "../shared/api/api";
import { renderWithProviders } from "./test-utils";

afterEach(() => {
	vi.restoreAllMocks();
});

describe("TrustPanel", () => {
	it("renders nothing while the request is in flight", () => {
		vi.spyOn(api, "getTrust").mockReturnValue(new Promise(() => {}));
		renderWithProviders(<TrustPanel />);
		expect(screen.queryByText(/Data Freshness/)).toBeNull();
		expect(screen.queryByRole("complementary")).toBeNull();
	});

	it("renders row counts and formatted match rate", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue({
			origence_row_count: 1234,
			symitar_row_count: 9876,
			reconciliation_match_rate: 0.913,
			known_caveats: [],
		});
		renderWithProviders(<TrustPanel />);
		await waitFor(() => screen.getByText(/Origence records/));
		expect(screen.getByText(/Origence records: 1,234/)).toBeInTheDocument();
		expect(screen.getByText(/Symitar records: 9,876/)).toBeInTheDocument();
		expect(
			screen.getByText(/Reconciliation match rate: 91.3%/),
		).toBeInTheDocument();
	});

	it("hides the caveats summary when the list is empty", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue({
			origence_row_count: 1,
			symitar_row_count: 1,
			reconciliation_match_rate: 1,
			known_caveats: [],
		});
		renderWithProviders(<TrustPanel />);
		await waitFor(() => screen.getByText(/Origence records/));
		expect(screen.queryByText(/Known caveats/)).not.toBeInTheDocument();
	});

	it("expands the caveats list when the summary is clicked", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue({
			origence_row_count: 1,
			symitar_row_count: 1,
			reconciliation_match_rate: 1,
			known_caveats: ["Exclude pending.", "Deposits are Symitar-only."],
		});
		const user = userEvent.setup();
		renderWithProviders(<TrustPanel />);
		await waitFor(() => screen.getByText(/Known caveats \(2\)/));
		await user.click(screen.getByText(/Known caveats \(2\)/));
		expect(screen.getByText("Exclude pending.")).toBeInTheDocument();
		expect(screen.getByText("Deposits are Symitar-only.")).toBeInTheDocument();
	});

	it("renders nothing when getTrust rejects", async () => {
		vi.spyOn(api, "getTrust").mockRejectedValue(new Error("boom"));
		renderWithProviders(<TrustPanel />);
		// Allow the rejected promise to settle
		await new Promise((r) => setTimeout(r, 50));
		expect(screen.queryByText(/Data Freshness/)).toBeNull();
		expect(screen.queryByRole("complementary")).toBeNull();
	});
});
