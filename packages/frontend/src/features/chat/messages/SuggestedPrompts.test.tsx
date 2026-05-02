import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as telemetry from "../../../shared/telemetry/client";
import SuggestedPrompts, { PROMPTS } from "./SuggestedPrompts";

afterEach(() => {
	vi.restoreAllMocks();
});

describe("SuggestedPrompts", () => {
	it("renders six starter chips per the spec", () => {
		render(<SuggestedPrompts onSelect={vi.fn()} />);
		expect(PROMPTS).toHaveLength(6);
		for (const prompt of PROMPTS) {
			expect(screen.getByRole("button", { name: prompt })).toBeInTheDocument();
		}
	});

	it("renders an accessible labelled section", () => {
		render(<SuggestedPrompts onSelect={vi.fn()} />);
		expect(
			screen.getByRole("region", { name: "Suggested prompts" }),
		).toBeInTheDocument();
	});

	it("calls onSelect with the chip text when clicked", () => {
		const onSelect = vi.fn();
		render(<SuggestedPrompts onSelect={onSelect} />);
		const firstPrompt = PROMPTS[0] ?? "";
		fireEvent.click(screen.getByRole("button", { name: firstPrompt }));
		expect(onSelect).toHaveBeenCalledWith(firstPrompt);
	});

	it("emits chat.suggested_prompt.clicked telemetry on click", () => {
		const spy = vi.spyOn(telemetry, "emit");
		render(<SuggestedPrompts onSelect={vi.fn()} />);
		const firstPrompt = PROMPTS[0] ?? "";
		fireEvent.click(screen.getByRole("button", { name: firstPrompt }));
		expect(spy).toHaveBeenCalledWith({
			type: "chat.suggested_prompt.clicked",
			prompt: firstPrompt,
		});
	});
});
