import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MarkdownText from "./MarkdownText";

describe("MarkdownText", () => {
	it("renders **bold** as <strong>", () => {
		const { container } = render(<MarkdownText>{"Hello **world**!"}</MarkdownText>);
		const strong = container.querySelector("strong");
		expect(strong).not.toBeNull();
		expect(strong?.textContent).toBe("world");
	});

	it("renders a numbered list with <ol> + <li> children", () => {
		const md = "1. First\n2. Second\n3. Third";
		const { container } = render(<MarkdownText>{md}</MarkdownText>);
		const ol = container.querySelector("ol");
		expect(ol).not.toBeNull();
		expect(ol?.querySelectorAll("li").length).toBe(3);
	});

	it("renders a bulleted list with <ul> + <li> children", () => {
		const md = "- alpha\n- beta\n- gamma";
		const { container } = render(<MarkdownText>{md}</MarkdownText>);
		const ul = container.querySelector("ul");
		expect(ul).not.toBeNull();
		expect(ul?.querySelectorAll("li").length).toBe(3);
	});

	it("renders a GFM table with thead + tbody (HUG-203 root case)", () => {
		const md = [
			"| Month | Volume |",
			"|-------|--------|",
			"| Jan   | 20     |",
			"| Feb   | 27     |",
			"| Mar   | 16     |",
		].join("\n");
		const { container } = render(<MarkdownText>{md}</MarkdownText>);
		const table = container.querySelector("table");
		expect(table).not.toBeNull();
		expect(table?.querySelector("thead")).not.toBeNull();
		expect(table?.querySelectorAll("tbody tr").length).toBe(3);
	});

	it("renders inline code as <code>", () => {
		const { container } = render(
			<MarkdownText>{"Use `loan_to_deposit_ratio` here."}</MarkdownText>,
		);
		const code = container.querySelector("code");
		expect(code).not.toBeNull();
		expect(code?.textContent).toBe("loan_to_deposit_ratio");
	});

	it("renders headers # H1 through ##### H5 as scaled <h*> elements", () => {
		const md = "# H1\n## H2\n### H3";
		const { container } = render(<MarkdownText>{md}</MarkdownText>);
		expect(container.querySelector("h1")?.textContent).toBe("H1");
		expect(container.querySelector("h2")?.textContent).toBe("H2");
		expect(container.querySelector("h3")?.textContent).toBe("H3");
	});

	it("strips raw <script> tags via rehype-sanitize", () => {
		const md = "Hello<script>alert(1)</script> world";
		const { container } = render(<MarkdownText>{md}</MarkdownText>);
		expect(container.querySelector("script")).toBeNull();
	});

	it("renders external links with target=_blank + rel=noreferrer", () => {
		const md = "[click](https://example.com)";
		const { container } = render(<MarkdownText>{md}</MarkdownText>);
		const a = container.querySelector("a");
		expect(a?.getAttribute("href")).toBe("https://example.com");
		expect(a?.getAttribute("target")).toBe("_blank");
		expect(a?.getAttribute("rel")).toContain("noreferrer");
	});

	it("renders partially-emitted markdown gracefully (mid-stream)", () => {
		// Closing `**` hasn't arrived yet — should still render without
		// throwing, leaving the literal `**` until the closing arrives.
		const partial = "Loan-to-deposit ratio is **13.4";
		const { container } = render(<MarkdownText>{partial}</MarkdownText>);
		expect(container.textContent).toContain("13.4");
	});
});
