import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import DataTable from "./DataTable";

function withMantine(ui: React.ReactElement) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

const rows = [
	{ name: "Charlie", score: 30 },
	{ name: "Alice", score: 10 },
	{ name: "Bob", score: 20 },
];

describe("DataTable", () => {
	it("renders column headers", () => {
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		expect(screen.getByRole("button", { name: /name/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /score/i })).toBeInTheDocument();
	});

	it("renders rows in initial order", () => {
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		const cells = screen.getAllByRole("cell");
		expect(cells[0]).toHaveTextContent("Charlie");
		expect(cells[2]).toHaveTextContent("Alice");
		expect(cells[4]).toHaveTextContent("Bob");
	});

	it("sorts ascending by string column on first click", async () => {
		const user = userEvent.setup();
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		await user.click(screen.getByRole("button", { name: /name/i }));
		const cells = screen.getAllByRole("cell");
		expect(cells[0]).toHaveTextContent("Alice");
	});

	it("sorts descending on second click of same column", async () => {
		const user = userEvent.setup();
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		await user.click(screen.getByRole("button", { name: /name/i }));
		await user.click(screen.getByRole("button", { name: /name/i }));
		const cells = screen.getAllByRole("cell");
		expect(cells[0]).toHaveTextContent("Charlie");
	});

	it("sorts ascending by numeric column", async () => {
		const user = userEvent.setup();
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		await user.click(screen.getByRole("button", { name: /score/i }));
		const cells = screen.getAllByRole("cell");
		expect(cells[1]).toHaveTextContent("10");
	});

	it("renders 'No data' when rows is empty", () => {
		withMantine(<DataTable columns={["name"]} rows={[]} />);
		expect(screen.getByText("No data")).toBeInTheDocument();
	});

	it("shows loading placeholder when loading=true", () => {
		withMantine(<DataTable columns={["name"]} rows={rows} loading={true} />);
		expect(screen.getByRole("status")).toBeInTheDocument();
		expect(screen.queryByRole("table")).toBeNull();
	});

	it("caps rows at 25", () => {
		const manyRows = Array.from({ length: 30 }, (_, i) => ({ n: i }));
		withMantine(<DataTable columns={["n"]} rows={manyRows} />);
		const cells = screen.getAllByRole("cell");
		expect(cells).toHaveLength(25);
	});

	it("density toggle button is present", () => {
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		expect(
			screen.getByRole("button", { name: /density toggle/i }),
		).toBeInTheDocument();
	});

	it("density toggle switches between compact and default", async () => {
		const user = userEvent.setup();
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		const btn = screen.getByRole("button", { name: /density toggle/i });
		expect(btn).toHaveAttribute("aria-pressed", "false");
		await user.click(btn);
		expect(btn).toHaveAttribute("aria-pressed", "true");
		await user.click(btn);
		expect(btn).toHaveAttribute("aria-pressed", "false");
	});

	it("thead is rendered (sticky header)", () => {
		withMantine(<DataTable columns={["name", "score"]} rows={rows} />);
		expect(screen.getByRole("table")).toBeInTheDocument();
		const thead = document.querySelector("thead");
		expect(thead).toBeInTheDocument();
	});
});
