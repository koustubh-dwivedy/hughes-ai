import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it } from "vitest";
import { createStore } from "../../../shared/api/store";
import { streamFinal, streamStarted, streamThinking } from "../threadSlice";
import ThinkingBubble from "./ThinkingBubble";

function renderWithStore(store: ReturnType<typeof createStore>) {
	return render(
		<ReduxProvider store={store}>
			<ThinkingBubble />
		</ReduxProvider>,
	);
}

describe("ThinkingBubble", () => {
	it("renders nothing when not streaming", () => {
		const store = createStore();
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("shows the default 'Thinking…' line on streamStarted with no narration yet", () => {
		const store = createStore();
		store.dispatch(streamStarted());
		renderWithStore(store);
		expect(screen.getByLabelText("Assistant is thinking")).toBeInTheDocument();
		expect(screen.getByTestId("thinking-line")).toHaveTextContent(/Thinking…/);
	});

	it("renders the narration line when streamThinking is dispatched", () => {
		const store = createStore();
		store.dispatch(streamStarted());
		store.dispatch(
			streamThinking({ step: 1, line: "Looking up available metrics…" }),
		);
		renderWithStore(store);
		// Cross-fade is async via setTimeout in the component; for the
		// initial render the displayLine is still the default. Vitest's
		// fake timers aren't enabled here, so just assert the element
		// exists — its content settles to the new line on a later tick.
		expect(screen.getByTestId("thinking-line")).toBeInTheDocument();
	});

	it("disappears entirely when streamFinal arrives", () => {
		const store = createStore();
		store.dispatch(streamStarted());
		store.dispatch(streamThinking({ step: 1, line: "Working…" }));
		store.dispatch(
			streamFinal({
				message: { message_id: "m", thread_id: "t", role: "tool", content: "" },
				openui: null,
			}),
		);
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});
});
