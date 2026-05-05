import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createStore } from "../../../shared/api/store";
import ThreadRail from "./ThreadRail";

vi.mock("../api", async () => {
	const actual = await vi.importActual<typeof import("../api")>("../api");
	return {
		...actual,
		useListThreadsQuery: vi.fn(),
	};
});

import { useListThreadsQuery } from "../api";
const mockHook = useListThreadsQuery as unknown as ReturnType<typeof vi.fn>;

afterEach(() => {
	vi.restoreAllMocks();
	mockHook.mockReset();
});

function renderRail(props: {
	currentThreadId: string | null;
	onNewThread?: () => void;
}) {
	const store = createStore();
	return render(
		<ReduxProvider store={store}>
			<MemoryRouter>
				<ThreadRail
					currentThreadId={props.currentThreadId}
					onNewThread={props.onNewThread ?? vi.fn()}
				/>
			</MemoryRouter>
		</ReduxProvider>,
	);
}

describe("ThreadRail", () => {
	it("shows 'No threads yet.' when the list is empty", () => {
		mockHook.mockReturnValue({
			data: { threads: [] },
			isLoading: false,
			isError: false,
		});
		renderRail({ currentThreadId: null });
		expect(screen.getByText(/No threads yet/)).toBeInTheDocument();
	});

	it("renders Loading… while the query is in flight", () => {
		mockHook.mockReturnValue({
			data: undefined,
			isLoading: true,
			isError: false,
		});
		renderRail({ currentThreadId: null });
		expect(screen.getByText(/Loading…/)).toBeInTheDocument();
	});

	it("renders an error fallback when the list query errors", () => {
		mockHook.mockReturnValue({
			data: undefined,
			isLoading: false,
			isError: true,
		});
		renderRail({ currentThreadId: null });
		expect(screen.getByText(/Couldn’t load threads/)).toBeInTheDocument();
	});

	it("renders each thread as a navigation link with the title or short id fallback", () => {
		mockHook.mockReturnValue({
			data: {
				threads: [
					{
						thread_id: "11111111-aaaa-bbbb-cccc-deadbeef0001",
						title: "Past-due investigation",
						started_at: "2026-05-06T00:00:00Z",
						last_active_at: "2026-05-06T00:01:00Z",
					},
					{
						thread_id: "22222222-bbbb-cccc-dddd-deadbeef0002",
						title: null,
						started_at: "2026-05-05T00:00:00Z",
						last_active_at: "2026-05-05T00:01:00Z",
					},
				],
			},
			isLoading: false,
			isError: false,
		});
		renderRail({ currentThreadId: "22222222-bbbb-cccc-dddd-deadbeef0002" });
		const titled = screen.getByRole("link", { name: "Past-due investigation" });
		expect(titled).toHaveAttribute(
			"href",
			"/intelligence/11111111-aaaa-bbbb-cccc-deadbeef0001",
		);
		const fallback = screen.getByRole("link", { name: "Thread 22222222" });
		expect(fallback).toHaveAttribute("aria-current", "page");
	});

	it("invokes onNewThread when the New thread button is clicked", () => {
		mockHook.mockReturnValue({
			data: { threads: [] },
			isLoading: false,
			isError: false,
		});
		const onNewThread = vi.fn();
		renderRail({ currentThreadId: null, onNewThread });
		screen.getByRole("button", { name: "+ New thread" }).click();
		expect(onNewThread).toHaveBeenCalled();
	});
});
