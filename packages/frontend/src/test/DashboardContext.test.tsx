import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import {
	DashboardContextProvider,
	useDashboardContext,
} from "../context/DashboardContext";
import { useDashboard } from "../hooks/useDashboard";
import type { DashboardEnvelope, DashboardParams } from "../lib/dashboardApi";

function TestRouter({
	initialUrl = "/",
	children,
}: {
	initialUrl?: string;
	children: ReactNode;
}) {
	return (
		<MemoryRouter initialEntries={[initialUrl]}>
			<Routes>
				<Route
					path="*"
					element={
						<DashboardContextProvider>{children}</DashboardContextProvider>
					}
				/>
			</Routes>
		</MemoryRouter>
	);
}

describe("DashboardContext", () => {
	it("default asOfDate and latestAvailable are undefined when no URL param", () => {
		function Reader() {
			const { asOfDate, latestAvailable } = useDashboardContext();
			return (
				<div data-testid="val">
					{String(asOfDate)}|{String(latestAvailable)}
				</div>
			);
		}
		render(
			<TestRouter>
				<Reader />
			</TestRouter>,
		);
		expect(screen.getByTestId("val").textContent).toBe("undefined|undefined");
	});

	it("URL ?as_of_date param is exposed via context", () => {
		function Reader() {
			const { asOfDate } = useDashboardContext();
			return <div data-testid="val">{asOfDate ?? "none"}</div>;
		}
		render(
			<TestRouter initialUrl="/?as_of_date=2026-04-01">
				<Reader />
			</TestRouter>,
		);
		expect(screen.getByTestId("val").textContent).toBe("2026-04-01");
	});

	it("setAsOfDate change triggers useDashboard refetch", async () => {
		type Payload = { v: number };
		const fetcher = vi.fn(
			(_p?: DashboardParams): Promise<DashboardEnvelope<Payload>> =>
				Promise.resolve({
					data: { v: 1 },
					as_of_date: "2026-03-01",
					generated_at: "",
					audit_id: "",
				}),
		);
		function Consumer() {
			const { asOfDate, setAsOfDate } = useDashboardContext();
			useDashboard(fetcher, { asOfDate });
			return (
				<button type="button" onClick={() => setAsOfDate("2026-05-01")}>
					change
				</button>
			);
		}
		render(
			<TestRouter>
				<Consumer />
			</TestRouter>,
		);
		await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
		await userEvent.click(screen.getByRole("button", { name: "change" }));
		await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
	});
});
