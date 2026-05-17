import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it } from "vitest";
import { createStore } from "../../../shared/api/store";
import {
	setCurrentThread,
	streamFinal,
	streamPlanDrafted,
	streamStarted,
	streamSubagentCompleted,
	streamSubagentFailed,
	streamSubagentSpawned,
	streamThinking,
	streamTool,
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
			streamThinking({
				threadId: TID,
				step: 1,
				line: "Looking up available metrics…",
			}),
		);
		renderWithStore(store);
		expect(screen.getByTestId("thinking-line")).toBeInTheDocument();
	});

	it("disappears entirely when streamFinal arrives", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(
			streamThinking({ threadId: TID, step: 1, line: "Working…" }),
		);
		store.dispatch(
			streamFinal({
				threadId: TID,
				final: {
					message: {
						message_id: "m",
						thread_id: TID,
						role: "tool",
						content: "",
					},
					openui: null,
				},
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
		store.dispatch(
			streamThinking({ threadId: TID, step: 1, line: "Working…" }),
		);
		const { container } = renderWithStore(store);
		expect(container).toBeEmptyDOMElement();
	});

	it("reappears when the user returns to the streaming thread", () => {
		const store = storeViewing("t-other");
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(
			streamThinking({ threadId: TID, step: 1, line: "Working…" }),
		);
		store.dispatch(setCurrentThread(TID));
		renderWithStore(store);
		expect(screen.getByLabelText("Assistant is thinking")).toBeInTheDocument();
	});

	// ── Bug 4 (2026-05-17): live activity panel ──────────────────────

	it("renders the plan badge when livePlan is populated", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(
			streamPlanDrafted({
				threadId: TID,
				plan: { plan_id: "p1", version: 2, step_count: 5 },
			}),
		);
		renderWithStore(store);
		const badge = screen.getByTestId("live-plan-badge");
		expect(badge).toHaveTextContent(/Plan v2 drafted.*5 steps/);
	});

	it("renders a subagent row per spawned worker with correct icon", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(
			streamSubagentSpawned({
				threadId: TID,
				call_id: "c1",
				prompt: "fetch branch A",
			}),
		);
		store.dispatch(
			streamSubagentSpawned({
				threadId: TID,
				call_id: "c2",
				prompt: "fetch branch B",
			}),
		);
		store.dispatch(streamSubagentCompleted({ threadId: TID, call_id: "c1" }));
		store.dispatch(
			streamSubagentFailed({
				threadId: TID,
				call_id: "c2",
				error: "metric not found",
			}),
		);
		renderWithStore(store);
		const rows = screen.getAllByTestId("live-subagent-row");
		expect(rows).toHaveLength(2);
		expect(screen.getByText(/fetch branch A/)).toBeInTheDocument();
		expect(screen.getByText(/fetch branch B/)).toBeInTheDocument();
	});

	it("renders the current tool line when liveCurrentTool is set", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		store.dispatch(streamTool({ threadId: TID, name: "run_subagent" }));
		renderWithStore(store);
		expect(screen.getByTestId("live-current-tool")).toHaveTextContent(
			/run_subagent/,
		);
	});

	it("activity panel is hidden until at least one live field is set", () => {
		const store = storeViewing(TID);
		store.dispatch(streamStarted({ threadId: TID }));
		renderWithStore(store);
		expect(screen.queryByTestId("thinking-activity-panel")).toBeNull();
	});
});
