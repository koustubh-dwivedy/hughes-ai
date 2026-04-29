import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import AppLayout from "../layout/AppLayout";

function renderLayout(path = "/") {
	return render(
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
});
