import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it } from "vitest";
import { createStore } from "../../../shared/api/store";
import {
	type ThreadStreamStep,
	setCurrentThread,
	streamStarted,
	streamStep,
} from "../threadSlice";
import StepIndicator from "./StepIndicator";

const TID = "t1";

function renderWithStore(store: ReturnType<typeof createStore>) {
	return render(
		<ReduxProvider store={store}>
			<StepIndicator />
		</ReduxProvider>,
	);
}

function storeViewing(threadId: string): ReturnType<typeof createStore> {
	const s = createStore();
	s.dispatch(setCurrentThread(threadId));
	return s;
}

const callList: ThreadStreamStep = {
	step: 1,
	kind: "tool_call",
	name: "list_metrics",
	args: {},
	result: null,
};

const callMf: ThreadStreamStep = {
	step: 3,
	kind: "tool_call",
	name: "mf_query",
	args: {},
	result: null,
};

describe("StepIndicator", () => {
	it("renders nothing when not streaming and no steps buffered", () => {
		const store = createStore();
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("renders nothing while streaming if no step events have arrived yet", () => {
		// HUG-201: the generic "Thinking…" copy moved to <ThinkingBubble>.
		// StepIndicator only renders once concrete tool-call events exist.
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("renders human labels for known tool kinds", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(streamStep({ threadId: TID, step: callList }));
		store.dispatch(streamStep({ threadId: TID, step: callMf }));
		renderWithStore(store);
		expect(
			screen.getByText(/Looking up available metrics…/),
		).toBeInTheDocument();
		expect(screen.getByText(/Querying MetricFlow…/)).toBeInTheDocument();
	});

	it("falls back to a tool name when the step is an unknown tool_call", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(
			streamStep({
				threadId: TID,
				step: {
					step: 1,
					kind: "tool_call",
					name: "future_tool",
					args: {},
					result: null,
				},
			}),
		);
		renderWithStore(store);
		expect(screen.getByText(/Calling future_tool…/)).toBeInTheDocument();
	});
});
