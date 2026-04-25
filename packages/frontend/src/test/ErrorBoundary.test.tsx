import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ErrorBoundary from "../components/ErrorBoundary";

vi.mock("../lib/logger", () => ({ default: { warn: vi.fn(), error: vi.fn() } }));

function Bomb({ shouldThrow }: { shouldThrow: boolean }) {
	if (shouldThrow) throw new Error("test explosion");
	return <p>all good</p>;
}

describe("ErrorBoundary", () => {
	it("renders children when there is no error", () => {
		render(
			<ErrorBoundary>
				<Bomb shouldThrow={false} />
			</ErrorBoundary>,
		);
		expect(screen.getByText("all good")).toBeInTheDocument();
	});

	it("renders fallback UI when child throws", () => {
		// suppress expected console.error from React
		const spy = vi.spyOn(console, "error").mockImplementation(() => {});
		render(
			<ErrorBoundary>
				<Bomb shouldThrow={true} />
			</ErrorBoundary>,
		);
		expect(screen.getByRole("alert")).toBeInTheDocument();
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();
		expect(screen.getByText("test explosion")).toBeInTheDocument();
		spy.mockRestore();
	});

	it("Try again resets the boundary without crashing the app", async () => {
		const user = userEvent.setup();
		const spy = vi.spyOn(console, "error").mockImplementation(() => {});
		render(
			<ErrorBoundary>
				<Bomb shouldThrow={true} />
			</ErrorBoundary>,
		);
		// Click Try again — boundary resets, child re-throws, boundary re-catches
		await user.click(screen.getByRole("button", { name: "Try again" }));
		// Fallback UI is still shown (child still throws) — no uncaught error
		expect(screen.getByRole("alert")).toBeInTheDocument();
		spy.mockRestore();
	});
});
