import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import AppLayout from "../app/AppLayout";
import { renderWithProviders, screen } from "./test-utils";

function renderLayout(path = "/") {
	return renderWithProviders(
		<MemoryRouter initialEntries={[path]}>
			<Routes>
				<Route element={<AppLayout />}>
					<Route path="/" element={<div>test-content</div>} />
					<Route path="/chat" element={<div>chat-content</div>} />
				</Route>
			</Routes>
		</MemoryRouter>,
	);
}

describe("AppLayout", () => {
	it("renders outlet child content", () => {
		renderLayout("/");
		expect(screen.getByText("test-content")).toBeInTheDocument();
	});

	it("renders the side nav", () => {
		renderLayout("/");
		expect(
			screen.getByRole("navigation", { name: "primary" }),
		).toBeInTheDocument();
	});

	it("renders child for nested route", () => {
		renderLayout("/chat");
		expect(screen.getByText("chat-content")).toBeInTheDocument();
	});

	it("renders main landmark", () => {
		renderLayout("/");
		expect(screen.getByRole("main")).toBeInTheDocument();
	});

	it("deep-links to /dashboards/deposits", () => {
		renderWithProviders(
			<MemoryRouter initialEntries={["/dashboards/deposits"]}>
				<Routes>
					<Route element={<AppLayout />}>
						<Route path="/dashboards/executive" element={<div>exec</div>} />
						<Route path="/dashboards/deposits" element={<div>deposits</div>} />
					</Route>
				</Routes>
			</MemoryRouter>,
		);
		expect(screen.getByText("deposits")).toBeInTheDocument();
	});

	it("/ redirects to executive summary route", () => {
		renderWithProviders(
			<MemoryRouter initialEntries={["/"]}>
				<Routes>
					<Route element={<AppLayout />}>
						<Route
							path="/"
							element={<Navigate to="/dashboards/executive" replace />}
						/>
						<Route path="/dashboards/executive" element={<div>exec</div>} />
					</Route>
				</Routes>
			</MemoryRouter>,
		);
		expect(screen.getByText("exec")).toBeInTheDocument();
	});
});
