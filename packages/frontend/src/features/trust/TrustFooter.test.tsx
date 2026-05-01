import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../shared/api/api";
import { renderWithProviders } from "../../test/test-utils";
import TrustFooter from "./TrustFooter";

afterEach(() => {
	vi.restoreAllMocks();
});

const TRUST_DATA: api.TrustResponse = {
	origence_row_count: 1_234,
	symitar_row_count: 9_876,
	reconciliation_match_rate: 0.991,
	known_caveats: ["Exclude pending.", "Deposits are Symitar-only."],
};

describe("TrustFooter", () => {
	it("renders nothing while data is loading", () => {
		vi.spyOn(api, "getTrust").mockReturnValue(new Promise(() => {}));
		renderWithProviders(<TrustFooter />);
		expect(screen.queryByRole("button")).toBeNull();
	});

	it("renders footer with reconciliation match rate", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue(TRUST_DATA);
		renderWithProviders(<TrustFooter />);
		await waitFor(() => expect(screen.getByRole("button")).toBeInTheDocument());
		expect(screen.getByText(/99.1% reconciliation match/)).toBeInTheDocument();
	});

	it("shows caveat count in footer", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue(TRUST_DATA);
		renderWithProviders(<TrustFooter />);
		await waitFor(() =>
			expect(screen.getByText(/2 caveats/)).toBeInTheDocument(),
		);
	});

	it("hides caveat count when list is empty", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue({
			...TRUST_DATA,
			known_caveats: [],
		});
		renderWithProviders(<TrustFooter />);
		await waitFor(() => expect(screen.getByRole("button")).toBeInTheDocument());
		expect(screen.queryByText(/caveat/)).toBeNull();
	});

	it("clicking footer opens trust sheet", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue(TRUST_DATA);
		renderWithProviders(<TrustFooter />);
		const footer = await screen.findByRole("button");
		fireEvent.click(footer);
		await waitFor(() =>
			expect(screen.getByText("Data trust & freshness")).toBeInTheDocument(),
		);
	});

	it("trust sheet shows row counts and caveats", async () => {
		vi.spyOn(api, "getTrust").mockResolvedValue(TRUST_DATA);
		renderWithProviders(<TrustFooter />);
		fireEvent.click(await screen.findByRole("button"));
		await waitFor(() =>
			expect(screen.getByText(/Origence records/)).toBeInTheDocument(),
		);
		expect(screen.getByText(/1,234/)).toBeInTheDocument();
	});

	it("renders nothing when getTrust rejects", async () => {
		vi.spyOn(api, "getTrust").mockRejectedValue(new Error("boom"));
		renderWithProviders(<TrustFooter />);
		await new Promise((r) => setTimeout(r, 0));
		expect(screen.queryByRole("button")).toBeNull();
	});
});
