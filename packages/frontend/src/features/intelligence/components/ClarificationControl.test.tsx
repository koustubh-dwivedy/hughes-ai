import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ThreadMessageWire } from "../api";
import ClarificationControl from "./ClarificationControl";

function makeClarify(
	overrides: Partial<ThreadMessageWire> = {},
): ThreadMessageWire {
	return {
		message_id: "c1",
		thread_id: "t1",
		parent_message_id: null,
		role: "tool",
		content: JSON.stringify({
			question: "Which branch?",
			options: ["North", "South", "East"],
		}),
		tool_calls: null,
		tool_results: [{ name: "clarify" }],
		openui_dsl: null,
		mf_query: null,
		rows: null,
		created_at: "2026-05-06T00:00:00Z",
		...overrides,
	};
}

describe("ClarificationControl", () => {
	it("renders nothing when message is null", () => {
		const { container } = render(
			<ClarificationControl message={null} onSubmit={vi.fn()} />,
		);
		expect(container).toBeEmptyDOMElement();
	});

	it("renders nothing when the message is a final_answer (not a clarify)", () => {
		const final: ThreadMessageWire = makeClarify({
			tool_results: [{ name: "final_answer" }],
		});
		const { container } = render(
			<ClarificationControl message={final} onSubmit={vi.fn()} />,
		);
		expect(container).toBeEmptyDOMElement();
	});

	it("renders the question and each option as a button", () => {
		render(<ClarificationControl message={makeClarify()} onSubmit={vi.fn()} />);
		expect(screen.getByText(/Which branch\?/)).toBeInTheDocument();
		for (const opt of ["North", "South", "East"]) {
			expect(screen.getByRole("button", { name: opt })).toBeInTheDocument();
		}
	});

	it("invokes onSubmit with the clicked option", () => {
		const onSubmit = vi.fn();
		render(
			<ClarificationControl message={makeClarify()} onSubmit={onSubmit} />,
		);
		fireEvent.click(screen.getByRole("button", { name: "South" }));
		expect(onSubmit).toHaveBeenCalledWith("South");
	});

	it("renders nothing when options array is empty", () => {
		const empty = makeClarify({
			content: JSON.stringify({ question: "Pick one", options: [] }),
		});
		const { container } = render(
			<ClarificationControl message={empty} onSubmit={vi.fn()} />,
		);
		expect(container).toBeEmptyDOMElement();
	});

	it("falls back to a default question when content is malformed", () => {
		const broken = makeClarify({ content: "not-json" });
		const { container } = render(
			<ClarificationControl message={broken} onSubmit={vi.fn()} />,
		);
		// Malformed → no options → no render.
		expect(container).toBeEmptyDOMElement();
	});
});
