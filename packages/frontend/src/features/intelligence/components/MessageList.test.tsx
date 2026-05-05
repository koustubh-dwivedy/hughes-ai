import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ThreadMessageWire } from "../api";
import MessageList from "./MessageList";

vi.mock("../openui/OpenUIRenderer", () => ({
	default: ({ dsl }: { dsl: string }) => (
		<div data-testid="mocked-openui">{dsl}</div>
	),
}));

vi.mock("shiki", () => ({
	codeToHtml: vi.fn(async (code: string) => `<pre><code>${code}</code></pre>`),
}));

const userMsg: ThreadMessageWire = {
	message_id: "u1",
	thread_id: "t1",
	parent_message_id: null,
	role: "user",
	content: "What is the loan-to-deposit ratio?",
	tool_calls: null,
	tool_results: null,
	openui_dsl: null,
	mf_query: null,
	rows: null,
	created_at: "2026-05-06T00:00:00Z",
};

function makeFinalAnswer(
	overrides: Partial<ThreadMessageWire> = {},
): ThreadMessageWire {
	return {
		message_id: "t-final",
		thread_id: "t1",
		parent_message_id: null,
		role: "tool",
		content: JSON.stringify({
			summary: "LTD ratio is 13.48%",
			openui_dsl: 'root = Stack(["13.48%"], "column", "m")',
			mf_query: { metric: "loan_to_deposit_ratio", limit: 1 },
			rows: [{ loan_to_deposit_ratio: 0.1348 }],
		}),
		tool_calls: null,
		tool_results: [{ name: "final_answer" }],
		openui_dsl: null,
		mf_query: null,
		rows: null,
		created_at: "2026-05-06T00:00:01Z",
		...overrides,
	};
}

describe("MessageList", () => {
	it("renders a user bubble with the question text", () => {
		render(<MessageList messages={[userMsg]} />);
		expect(
			screen.getByLabelText("User question"),
		).toHaveTextContent(/loan-to-deposit/i);
	});

	it("renders an assistant terminal message with summary, OpenUI tree, rows, and MF query disclosure", () => {
		render(<MessageList messages={[userMsg, makeFinalAnswer()]} />);
		expect(screen.getByText(/LTD ratio is 13.48%/)).toBeInTheDocument();
		expect(screen.getByTestId("openui-renderer")).toBeInTheDocument();
		expect(screen.getByTestId("mocked-openui")).toHaveTextContent(/Stack/);
		// One label inside <summary>, another inside the <JsonBlock> header.
		expect(screen.getAllByText("MetricFlow query")).toHaveLength(2);
		// rows table renders the column header
		expect(screen.getByText("loan_to_deposit_ratio")).toBeInTheDocument();
	});

	it("prefers persisted columns over content blob when both are populated", () => {
		const msg = makeFinalAnswer({
			openui_dsl: 'root = TextContent("from-column")',
		});
		render(<MessageList messages={[msg]} />);
		expect(screen.getByTestId("mocked-openui")).toHaveTextContent("from-column");
	});

	it("renders a clarification turn (tool message that's not final_answer) as nothing user-visible", () => {
		const clarify: ThreadMessageWire = {
			...makeFinalAnswer({ tool_results: [{ name: "clarify" }] }),
			content: JSON.stringify({
				question: "Which branch?",
				options: ["A", "B"],
			}),
		};
		const { container } = render(<MessageList messages={[clarify]} />);
		// Clarifications are surfaced by <ClarificationControl>, not MessageList,
		// so MessageList should drop the tool row.
		expect(container.querySelector('[data-testid="openui-renderer"]'))
			.toBeNull();
		expect(screen.queryByText(/Which branch/)).toBeNull();
	});

	it("renders an assistant-role text message without an OpenUI tree", () => {
		const assistant: ThreadMessageWire = {
			...userMsg,
			role: "assistant",
			content: "Reasoning step text",
		};
		render(<MessageList messages={[assistant]} />);
		expect(screen.getByLabelText("Assistant message")).toHaveTextContent(
			"Reasoning step text",
		);
		expect(screen.queryByTestId("openui-renderer")).toBeNull();
	});

	it("falls back to parsing content when persisted columns are empty (no DSL → no renderer)", () => {
		const msg = makeFinalAnswer({
			content: JSON.stringify({
				summary: "Pure text answer",
				openui_dsl: null,
				mf_query: null,
				rows: null,
			}),
		});
		render(<MessageList messages={[msg]} />);
		expect(screen.getByText("Pure text answer")).toBeInTheDocument();
		expect(screen.queryByTestId("openui-renderer")).toBeNull();
		expect(screen.queryByText("MetricFlow query")).toBeNull();
	});
});
