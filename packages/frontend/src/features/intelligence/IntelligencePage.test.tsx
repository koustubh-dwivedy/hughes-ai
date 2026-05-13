/**
 * Behavior tests for the auto-scroll added to keep the ThinkingBubble
 * (and live narration) in view on follow-up turns. Pre-fix the bubble
 * landed below the fold on second+ turns because the conversation pane
 * uses `overflow-y: auto` which doesn't auto-scroll on content growth.
 *
 * jsdom doesn't compute layout, so we mock `scrollHeight` to a fixed
 * value and assert the effect assigns `scrollTop = scrollHeight` when
 * the user was at the tail, and leaves it alone when they weren't.
 */

import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
} from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createStore } from "../../shared/api/store";
import IntelligencePage from "./IntelligencePage";
import { streamStarted } from "./threadSlice";

afterEach(() => {
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

const FIXED_SCROLL_HEIGHT = 800;

function mockThreadFetch(): void {
	// Each render fetches /threads (sidebar list) and /threads/:id
	// (hydrate). Return the minimum payload each one needs.
	vi.spyOn(global, "fetch").mockImplementation(
		async (input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url.endsWith("/threads") || url.includes("/threads?")) {
				return new Response(JSON.stringify({ threads: [] }), {
					status: 200,
					headers: { "Content-Type": "application/json" },
				});
			}
			// /threads/:id — keep messages.length == 1 so the first auto-scroll
			// effect fires once on mount and we can verify the second-turn
			// behavior in isolation.
			return new Response(
				JSON.stringify({
					thread_id: "t1",
					title: "test thread",
					started_at: "2026-05-13T00:00:00Z",
					last_active_at: "2026-05-13T00:00:00Z",
					messages: [
						{
							message_id: "m1",
							thread_id: "t1",
							parent_message_id: null,
							role: "user",
							content: "prior question",
							tool_calls: null,
							tool_results: null,
							openui_dsl: null,
							mf_query: null,
							rows: null,
							created_at: "2026-05-13T00:00:00Z",
						},
					],
				}),
				{ status: 200, headers: { "Content-Type": "application/json" } },
			);
		},
	);
}

function pinScrollHeight(el: HTMLElement, value: number): void {
	Object.defineProperty(el, "scrollHeight", {
		configurable: true,
		get: () => value,
	});
}

function renderAt(threadId: string) {
	const store = createStore();
	const utils = render(
		<ReduxProvider store={store}>
			<MemoryRouter initialEntries={[`/intelligence/${threadId}`]}>
				<Routes>
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

describe("IntelligencePage — follow-tail auto-scroll", () => {
	it("scrolls the conversation pane to the bottom on streamStarted when user was at the tail", async () => {
		mockThreadFetch();
		const { store } = renderAt("t1");
		// Wait for the hydration fetch so the conversation pane is in
		// the DOM (it's behind the `!showEmptyState` branch).
		await waitFor(() =>
			expect(screen.getByTestId("conversation-pane")).toBeInTheDocument(),
		);
		const pane = screen.getByTestId("conversation-pane");
		pinScrollHeight(pane, FIXED_SCROLL_HEIGHT);
		// Reset whatever the mount effect did so we measure the
		// stream-start effect in isolation.
		pane.scrollTop = 0;
		act(() => {
			store.dispatch(streamStarted());
		});
		await waitFor(() => expect(pane.scrollTop).toBe(FIXED_SCROLL_HEIGHT));
	});

	it("force-scrolls on user submit even when the user had scrolled up to re-read history (issue 1 fix)", async () => {
		// Pre-fix the wasAtBottomRef guard returned early when the user
		// had scrolled up, so the new ThinkingBubble landed below the
		// fold. User-initiated transitions (streaming false→true,
		// pendingUserContent null→set) must override the guard because
		// they're a strong signal the user wants to follow the new turn.
		mockThreadFetch();
		const { store } = renderAt("t1");
		await waitFor(() =>
			expect(screen.getByTestId("conversation-pane")).toBeInTheDocument(),
		);
		const pane = screen.getByTestId("conversation-pane");
		pinScrollHeight(pane, FIXED_SCROLL_HEIGHT);
		Object.defineProperty(pane, "clientHeight", {
			configurable: true,
			get: () => 200,
		});
		// Simulate the user scrolling up to re-read prior history.
		pane.scrollTop = 100;
		fireEvent.scroll(pane);
		pane.scrollTop = 100;
		// User submits a follow-up — streaming flips true.
		act(() => {
			store.dispatch(streamStarted());
		});
		// Force-scroll fires regardless of prior scroll position.
		await waitFor(() => expect(pane.scrollTop).toBe(FIXED_SCROLL_HEIGHT));
	});
});
