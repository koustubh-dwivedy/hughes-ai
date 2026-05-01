import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Banner from "../components/Banner";

describe("Banner", () => {
	it("renders the message inside a note role", () => {
		render(<Banner message="Demo data only" />);
		const note = screen.getByRole("note");
		expect(note).toHaveTextContent("Demo data only");
	});

	it("uses warning palette when variant=warning", () => {
		render(<Banner message="Stale snapshot" variant="warning" />);
		const note = screen.getByRole("note");
		expect(note).toHaveStyle({ backgroundColor: "rgb(254, 249, 195)" });
		expect(note).toHaveStyle({ color: "rgb(133, 77, 14)" });
	});

	it("uses info palette by default", () => {
		render(<Banner message="Heads up" />);
		const note = screen.getByRole("note");
		expect(note).toHaveStyle({ backgroundColor: "rgb(239, 246, 255)" });
		expect(note).toHaveStyle({ color: "rgb(30, 64, 175)" });
	});
});
