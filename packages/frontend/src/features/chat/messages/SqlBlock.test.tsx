import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as telemetry from "../../../shared/telemetry/client";
import SqlBlock from "./SqlBlock";

vi.mock("shiki", () => ({
	codeToHtml: vi.fn(
		async (code: string) =>
			`<pre class="shiki"><code><span class="line"><span style="color:#d73a49">SELECT</span> ${code}</span></code></pre>`,
	),
}));

afterEach(() => {
	vi.restoreAllMocks();
});

describe("SqlBlock", () => {
	it("renders SQL with shiki-highlighted markup", async () => {
		render(<SqlBlock sql="SELECT 1 FROM t" queryId="q-1" />);
		await waitFor(() => {
			expect(document.querySelector(".shiki")).not.toBeNull();
		});
	});

	it("renders header label and copy button by default", () => {
		render(<SqlBlock sql="SELECT 1" queryId="q-1" />);
		expect(screen.getByText("SQL")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Copy SQL" }),
		).toBeInTheDocument();
	});

	it("does not render Open in editor when editorUrl is missing", () => {
		render(<SqlBlock sql="SELECT 1" queryId="q-1" />);
		expect(screen.queryByLabelText("Open SQL in editor")).toBeNull();
	});

	it("renders Open in editor link when editorUrl is provided", () => {
		render(
			<SqlBlock
				sql="SELECT 1"
				queryId="q-1"
				editorUrl="https://example.com/edit"
			/>,
		);
		const link = screen.getByLabelText("Open SQL in editor");
		expect(link).toHaveAttribute("href", "https://example.com/edit");
		expect(link).toHaveAttribute("target", "_blank");
		expect(link).toHaveAttribute("rel", "noopener noreferrer");
	});

	it("copy button writes SQL to clipboard and emits telemetry", async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		Object.assign(navigator, { clipboard: { writeText } });
		const emitSpy = vi.spyOn(telemetry, "emit");

		render(<SqlBlock sql="SELECT 42" queryId="q-42" />);
		fireEvent.click(screen.getByRole("button", { name: "Copy SQL" }));

		await waitFor(() => {
			expect(writeText).toHaveBeenCalledWith("SELECT 42");
		});
		expect(emitSpy).toHaveBeenCalledWith({
			type: "chat.sql.copied",
			query_id: "q-42",
		});
	});

	it("shows Copied state after a successful copy", async () => {
		Object.assign(navigator, {
			clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
		});
		render(<SqlBlock sql="SELECT 1" queryId="q-1" />);
		fireEvent.click(screen.getByRole("button", { name: "Copy SQL" }));
		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: "Copy SQL" }),
			).toHaveTextContent("Copied");
		});
	});

	it("does not emit telemetry when clipboard write fails", async () => {
		Object.assign(navigator, {
			clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
		});
		const emitSpy = vi.spyOn(telemetry, "emit");
		render(<SqlBlock sql="SELECT 1" queryId="q-1" />);
		fireEvent.click(screen.getByRole("button", { name: "Copy SQL" }));
		await new Promise((r) => setTimeout(r, 20));
		expect(emitSpy).not.toHaveBeenCalled();
	});
});
