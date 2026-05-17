/**
 * "+ New thread" regression suite. Extracted from
 * IntelligencePage.test.tsx so each file stays under the 300-line
 * structural cap. Covers the bug where clicking the button mid-stream
 * left the user on a blank panel instead of the starter screen.
 */

import { act, render, screen, waitFor } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createStore } from "../../shared/api/store";
import IntelligencePage from "./IntelligencePage";
import {
	pendingQuestionRebound,
	pendingQuestionSubmitted,
	streamStarted,
} from "./threadSlice";

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

vi.mock("./openui/OpenUIRenderer", () => ({
	default: ({ dsl }: { dsl: string }) => (
		<div data-testid="mocked-openui">{dsl}</div>
	),
}));

vi.mock("shiki", () => ({
	codeToHtml: vi.fn(async (code: string) => `<pre><code>${code}</code></pre>`),
}));

function mockThreadFetch(): void {
	const stub = vi.fn(async () => {
		return new Response(JSON.stringify({ threads: [] }), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		});
	});
	vi.stubGlobal("fetch", stub);
}

function renderAtRoot() {
	const store = createStore();
	const utils = render(
		<ReduxProvider store={store}>
			<MemoryRouter initialEntries={["/intelligence"]}>
				<Routes>
					<Route path="/intelligence" element={<IntelligencePage />} />
					<Route
						path="/intelligence/:threadId"
						element={<IntelligencePage />}
					/>
				</Routes>
			</MemoryRouter>
		</ReduxProvider>,
	);
	return { store, ...utils };
}

describe("IntelligencePage — '+ New thread' lands on starter questions", () => {
	it("shows starter questions on /intelligence even when a stream is alive on a different thread", async () => {
		mockThreadFetch();
		const { store } = renderAtRoot();
		act(() => {
			store.dispatch(streamStarted({ threadId: "t1" }));
			store.dispatch(
				pendingQuestionSubmitted({ content: "old Q", threadId: "t1" }),
			);
		});
		await waitFor(() =>
			expect(screen.getByText(/Ask Hughes/)).toBeInTheDocument(),
		);
		expect(
			screen.getAllByRole("button", {
				name: /Decompose|Compare|Summarise|How has/,
			}).length,
		).toBeGreaterThan(0);
	});

	it("after rebind, /intelligence shows starter questions again (the user's repro)", async () => {
		// Submit from empty state → createThread → rebind → "+ New thread"
		// puts the user back on /intelligence. Starter screen MUST render
		// because the pendingQuestion.threadId is now the real id, no
		// longer matching the null view.
		mockThreadFetch();
		const { store } = renderAtRoot();
		act(() => {
			store.dispatch(
				pendingQuestionSubmitted({ content: "first Q", threadId: null }),
			);
		});
		act(() => {
			store.dispatch(streamStarted({ threadId: "newId" }));
			store.dispatch(pendingQuestionRebound({ threadId: "newId" }));
		});
		await waitFor(() =>
			expect(screen.getByText(/Ask Hughes/)).toBeInTheDocument(),
		);
		expect(screen.queryByText(/first Q/)).toBeNull();
	});

	it("still hides the empty state while we're actively creating a thread from /intelligence", () => {
		mockThreadFetch();
		const { store } = renderAtRoot();
		act(() => {
			store.dispatch(
				pendingQuestionSubmitted({ content: "fresh Q", threadId: null }),
			);
		});
		expect(screen.queryByText(/Open-ended questions about loans/)).toBeNull();
	});
});
