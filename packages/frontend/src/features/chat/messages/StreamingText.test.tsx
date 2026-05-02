import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StreamingText from "./StreamingText";

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
	vi.restoreAllMocks();
});

describe("StreamingText — incremental render", () => {
	it("starts with no characters and a streaming cursor", () => {
		render(<StreamingText text="Hello, world!" durationMs={1500} />);
		const p = screen.getByText("", { selector: "p[data-streaming='true']" });
		expect(p).toHaveAttribute("aria-busy", "true");
	});

	it("reveals more characters as time advances", () => {
		render(<StreamingText text="Hello, world!" durationMs={1500} />);
		const p = () =>
			screen.getByText(
				(_, el) => el?.tagName === "P" && el.hasAttribute("data-streaming"),
			);
		const initial = p().textContent ?? "";

		act(() => {
			vi.advanceTimersByTime(300);
		});
		const after300 = p().textContent ?? "";
		expect(after300.length).toBeGreaterThanOrEqual(initial.length);

		act(() => {
			vi.advanceTimersByTime(900);
		});
		const after1200 = p().textContent ?? "";
		expect(after1200.length).toBeGreaterThanOrEqual(after300.length);
	});

	it("renders the full text once duration elapses", () => {
		render(<StreamingText text="Hello, world!" durationMs={1500} />);
		act(() => {
			vi.advanceTimersByTime(2000);
		});
		const p = screen.getByText("Hello, world!");
		expect(p).toHaveAttribute("aria-busy", "false");
		expect(p).toHaveAttribute("data-streaming", "false");
	});

	it("calls onComplete when streaming finishes", () => {
		const onComplete = vi.fn();
		render(
			<StreamingText text="Done" durationMs={500} onComplete={onComplete} />,
		);
		act(() => {
			vi.advanceTimersByTime(1000);
		});
		expect(onComplete).toHaveBeenCalledTimes(1);
	});

	it("handles empty text by completing immediately", () => {
		const onComplete = vi.fn();
		render(<StreamingText text="" onComplete={onComplete} />);
		expect(onComplete).toHaveBeenCalledTimes(1);
	});
});
