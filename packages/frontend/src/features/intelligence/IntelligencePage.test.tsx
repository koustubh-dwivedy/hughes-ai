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
import {
	pendingQuestionSubmitted,
	setCurrentThread,
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

const FIXED_SCROLL_HEIGHT = 800;

function mockThreadFetch(): void {
	// Replace global.fetch via vi.stubGlobal so it survives clean
	// across the suite's afterEach (vi.spyOn on the setup file's
	// vi.fn fetch doesn't always re-attach reliably between tests —
	// causing the singleton fallback's `{}` body to leak through and
	// crash ThreadRail on `data.threads.length`).
	const stub = vi.fn(async (input: RequestInfo | URL) => {
		const url =
			typeof input === "string"
				? input
				: input instanceof URL
					? input.href
					: input.url;
		if (url.endsWith("/threads") || url.includes("/threads?")) {
			return new Response(JSON.stringify({ threads: [] }), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			});
		}
		// /threads/:id — keep messages.length == 1 so the first
		// auto-scroll effect fires once on mount and we can verify
		// the second-turn behavior in isolation.
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
	});
	vi.stubGlobal("fetch", stub);
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

describe("IntelligencePage — cross-thread streaming visibility", () => {
	it("shows the thinking bubble on the streaming thread but NOT on a different one", async () => {
		// Issue 3 root case: A's stream is alive; user is viewing A.
		// Bubble is present. They switch to B (route change) — bubble
		// must not bleed across.
		mockThreadFetch();
		const { store } = renderAt("t1");
		await waitFor(() =>
			expect(screen.getByTestId("conversation-pane")).toBeInTheDocument(),
		);
		act(() => {
			store.dispatch(streamStarted({ threadId: "t1" }));
		});
		expect(screen.getByLabelText("Assistant is thinking")).toBeInTheDocument();
		// Now simulate switching to a different thread by dispatching
		// setCurrentThread directly. The thinking-bubble selector
		// should no longer match.
		act(() => {
			store.dispatch(setCurrentThread("t-other"));
		});
		expect(
			screen.queryByLabelText("Assistant is thinking"),
		).not.toBeInTheDocument();
	});

	it("preserves streaming state across thread switches — bubble reappears when user returns", async () => {
		// The slice no longer wipes buffers on setCurrentThread, so
		// streaming should resume rendering when the user navigates
		// back to the source thread mid-stream.
		mockThreadFetch();
		const { store } = renderAt("t1");
		await waitFor(() =>
			expect(screen.getByTestId("conversation-pane")).toBeInTheDocument(),
		);
		act(() => {
			store.dispatch(streamStarted({ threadId: "t1" }));
		});
		act(() => {
			store.dispatch(setCurrentThread("t-other"));
		});
		// State must still know streaming is alive on t1.
		expect(store.getState().thread.streaming).toBe(true);
		expect(store.getState().thread.streamingThreadId).toBe("t1");
		// User returns to t1.
		act(() => {
			store.dispatch(setCurrentThread("t1"));
		});
		expect(screen.getByLabelText("Assistant is thinking")).toBeInTheDocument();
	});
});

describe("IntelligencePage — '+ New thread' lands on starter questions", () => {
	it("shows starter questions on /intelligence even when a stream is alive on a different thread", async () => {
		// Reproduces: user is on thread A which is streaming, clicks
		// "+ New thread", lands on /intelligence — must see starter
		// questions, not a blank panel. Pre-fix the showEmptyState gate
		// suppressed the empty state whenever ANY pendingQuestion was
		// set, leaving the new view empty.
		mockThreadFetch();
		const { store } = renderAtRoot();
		// Simulate: an old thread (t1) is mid-stream + has a pending bubble.
		act(() => {
			store.dispatch(streamStarted({ threadId: "t1" }));
			store.dispatch(
				pendingQuestionSubmitted({ content: "old Q", threadId: "t1" }),
			);
		});
		// On /intelligence (no thread), starter questions must render.
		await waitFor(() =>
			expect(screen.getByText(/Ask Hughes/)).toBeInTheDocument(),
		);
		// Sanity: at least one starter button visible.
		expect(
			screen.getAllByRole("button", {
				name: /Decompose|Compare|Summarise|How has/,
			}).length,
		).toBeGreaterThan(0);
	});

	it("still hides the empty state while we're actively creating a thread from /intelligence", () => {
		// pendingQuestion.threadId === null means the user JUST clicked a
		// starter and we're mid-createThread. Empty state must NOT show in
		// that window — avoids a flash before the navigate lands.
		mockThreadFetch();
		const { store } = renderAtRoot();
		act(() => {
			store.dispatch(
				pendingQuestionSubmitted({ content: "fresh Q", threadId: null }),
			);
		});
		// Starter heading should NOT be visible — we're already submitting.
		expect(screen.queryByText(/Open-ended questions about loans/)).toBeNull();
	});
});

describe("IntelligencePage — per-thread composer gate", () => {
	it("composer is ENABLED when another thread is streaming (user can submit to this one)", async () => {
		mockThreadFetch();
		const { store } = renderAt("t1");
		await waitFor(() =>
			expect(screen.getByTestId("conversation-pane")).toBeInTheDocument(),
		);
		act(() => {
			store.dispatch(streamStarted({ threadId: "t-other" }));
		});
		const composer = screen.getByLabelText("Ask Hughes") as HTMLTextAreaElement;
		expect(composer.disabled).toBe(false);
	});

	it("composer is DISABLED when THIS thread is the one streaming", async () => {
		mockThreadFetch();
		const { store } = renderAt("t1");
		await waitFor(() =>
			expect(screen.getByTestId("conversation-pane")).toBeInTheDocument(),
		);
		act(() => {
			store.dispatch(streamStarted({ threadId: "t1" }));
		});
		const composer = screen.getByLabelText("Ask Hughes") as HTMLTextAreaElement;
		expect(composer.disabled).toBe(true);
	});
});

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
			store.dispatch(streamStarted({ threadId: "t1" }));
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
			store.dispatch(streamStarted({ threadId: "t1" }));
		});
		// Force-scroll fires regardless of prior scroll position.
		await waitFor(() => expect(pane.scrollTop).toBe(FIXED_SCROLL_HEIGHT));
	});
});
