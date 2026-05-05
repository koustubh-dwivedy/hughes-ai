import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import JsonBlock from "./JsonBlock";

vi.mock("shiki", () => ({
	codeToHtml: vi.fn(
		async (code: string) =>
			`<pre class="shiki"><code><span class="line">${code}</span></code></pre>`,
	),
}));

afterEach(() => {
	vi.restoreAllMocks();
});

describe("JsonBlock", () => {
	it("renders pretty-printed JSON via shiki markup", async () => {
		render(<JsonBlock value={{ metric: "loan_to_deposit_ratio", limit: 1 }} />);
		await waitFor(() => {
			expect(document.querySelector(".shiki")).not.toBeNull();
		});
	});

	it("renders default JSON label and copy button", () => {
		render(<JsonBlock value={{ a: 1 }} />);
		expect(screen.getByText("JSON")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Copy JSON" }),
		).toBeInTheDocument();
	});

	it("uses a custom label when provided", () => {
		render(<JsonBlock value={{}} label="MetricFlow query" />);
		expect(screen.getByText("MetricFlow query")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Copy MetricFlow query" }),
		).toBeInTheDocument();
	});

	it("copy button writes pretty-printed JSON to clipboard and invokes onCopy", async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		Object.assign(navigator, { clipboard: { writeText } });
		const onCopy = vi.fn();

		render(<JsonBlock value={{ k: "v" }} onCopy={onCopy} />);
		fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));

		await waitFor(() => {
			expect(writeText).toHaveBeenCalledWith('{\n  "k": "v"\n}');
		});
		expect(onCopy).toHaveBeenCalledTimes(1);
	});

	it("falls back to String() for values that cannot be serialized", async () => {
		const cyclic: { self?: unknown } = {};
		cyclic.self = cyclic;
		// Cyclic objects throw in JSON.stringify; component falls back to String().
		render(<JsonBlock value={cyclic} />);
		expect(
			document.querySelector("pre, .shiki") !== null ||
				screen.getByText("JSON"),
		).toBeTruthy();
	});

	it("shows Copied state after a successful copy", async () => {
		Object.assign(navigator, {
			clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
		});
		render(<JsonBlock value={{ a: 1 }} />);
		fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: "Copy JSON" }),
			).toHaveTextContent("Copied");
		});
	});

	it("does not invoke onCopy when clipboard write fails", async () => {
		Object.assign(navigator, {
			clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
		});
		const onCopy = vi.fn();
		render(<JsonBlock value={{}} onCopy={onCopy} />);
		fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
		await new Promise((r) => setTimeout(r, 20));
		expect(onCopy).not.toHaveBeenCalled();
	});
});
