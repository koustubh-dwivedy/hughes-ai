import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it } from "vitest";
import { createStore } from "../../../shared/api/store";
import {
	setCurrentThread,
	streamFinal,
	streamStarted,
	streamThinking,
} from "../threadSlice";
import ThinkingBubble from "./ThinkingBubble";

const TID = "t1";

function renderWithStore(store: ReturnType<typeof createStore>) {
	return render(
		<ReduxProvider store={store}>
			<ThinkingBubble />
		</ReduxProvider>,
	);
}

function storeViewing(threadId: string): ReturnType<typeof createStore> {
	const s = createStore();
	s.dispatch(setCurrentThread(threadId));
	return s;
}

describe("ThinkingBubble", () => {
	it("renders nothing when not streaming", () => {
		const store = storeViewing(TID);
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("shows the default 'Thinking…' line on streamStarted with no narration yet", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		renderWithStore(store);
		expect(screen.getByLabelText("Assistant is thinking")).toBeInTheDocument();
		expect(screen.getByTestId("thinking-line")).toHaveTextContent(/Thinking…/);
	});

	it("renders the narration line when streamThinking is dispatched", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(
			streamThinking({ step: 1, line: "Looking up available metrics…" }),
		);
		renderWithStore(store);
		expect(screen.getByTestId("thinking-line")).toBeInTheDocument();
	});

	it("disappears entirely when streamFinal arrives", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(streamThinking({ step: 1, line: "Working…" }));
		store.dispatch(
			streamFinal({
				message: { message_id: "m", thread_id: TID, role: "tool", content: "" },
				openui: null,
			}),
		);
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("renders nothing while a different thread's stream is in flight", () => {
		// Issue 3: stream alive on A, user viewing B. The bubble must
		// stay on A — never bleed into B. Pre-fix this was implicit
		// because setCurrentThread wiped streaming; now it's explicit.
		const store = storeViewing("t-other");
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(streamThinking({ step: 1, line: "Working…" }));
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("reappears when the user returns to the streaming thread", () => {
		const store = storeViewing("t-other");
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(streamThinking({ step: 1, line: "Working…" }));
		store.dispatch(setCurrentThread(TID));
		renderWithStore(store);
		expect(screen.getByLabelText("Assistant is thinking")).toBeInTheDocument();
	});
});
