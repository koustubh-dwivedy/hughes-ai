import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Tag from "./Tag";

describe("Tag", () => {
	it("renders the label", () => {
		render(<Tag label="Active" />);
		expect(screen.getByText("Active")).toBeInTheDocument();
	});

	it("variant=warning applies warning background color", () => {
		render(<Tag label="Overdue" variant="warning" />);
		const span = screen.getByText("Overdue").closest("span");
		expect(span).toHaveStyle({ backgroundColor: "#fffbeb" });
	});

	it("variant=danger applies danger color", () => {
		render(<Tag label="Delinquent" variant="danger" />);
		const span = screen.getByText("Delinquent").closest("span");
		expect(span).toHaveStyle({ color: "#e11d48" });
	});

	it("variant=success applies success background", () => {
		render(<Tag label="Current" variant="success" />);
		const span = screen.getByText("Current").closest("span");
		expect(span).toHaveStyle({ backgroundColor: "#f0fdf4" });
	});

	it("variant=info applies info border", () => {
		render(<Tag label="Review" variant="info" />);
		const span = screen.getByText("Review").closest("span");
		expect(span).toHaveStyle({ border: "1px solid #bae6fd" });
	});

	it("renders remove button when onRemove provided and fires callback", async () => {
		const user = userEvent.setup();
		const onRemove = vi.fn();
		render(<Tag label="Active" onRemove={onRemove} />);
		const btn = screen.getByRole("button", { name: "Remove Active" });
		expect(btn).toBeInTheDocument();
		await user.click(btn);
		expect(onRemove).toHaveBeenCalledOnce();
	});

	it("does not render remove button when onRemove omitted", () => {
		render(<Tag label="Active" />);
		expect(screen.queryByRole("button")).toBeNull();
	});

	it("size=md has larger font size than size=sm", () => {
		const { unmount } = render(<Tag label="Tag" size="md" />);
		const spanMd = screen.getByText("Tag").closest("span");
		const fontSizeMd = spanMd ? getComputedStyle(spanMd).fontSize : "";
		unmount();

		render(<Tag label="Tag" size="sm" />);
		const spanSm = screen.getByText("Tag").closest("span");
		const fontSizeSm = spanSm ? getComputedStyle(spanSm).fontSize : "";

		expect(fontSizeMd).not.toBe(fontSizeSm);
	});

	it("size=sm uses xs font size", () => {
		render(<Tag label="Small" size="sm" />);
		const span = screen.getByText("Small").closest("span");
		expect(span).toHaveStyle({ fontSize: "0.75rem" });
	});

	it("size=md uses sm font size", () => {
		render(<Tag label="Medium" size="md" />);
		const span = screen.getByText("Medium").closest("span");
		expect(span).toHaveStyle({ fontSize: "0.875rem" });
	});
});
