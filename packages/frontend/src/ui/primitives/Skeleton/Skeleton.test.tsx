import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Skeleton from "./Skeleton";

describe("Skeleton", () => {
	it("renders with role=status and aria-label=loading", () => {
		render(<Skeleton />);
		const el = screen.getByRole("status");
		expect(el).toBeInTheDocument();
		expect(el).toHaveAttribute("aria-label", "loading");
	});

	it("applies width as inline style", () => {
		render(<Skeleton width={200} />);
		const el = screen.getByRole("status");
		expect(el).toHaveStyle({ width: "200px" });
	});

	it("applies height as inline style", () => {
		render(<Skeleton height="3rem" />);
		const el = screen.getByRole("status");
		expect(el).toHaveStyle({ height: "3rem" });
	});

	it("applies string width", () => {
		render(<Skeleton width="50%" />);
		const el = screen.getByRole("status");
		expect(el).toHaveStyle({ width: "50%" });
	});

	it("has animation when animated=true", () => {
		render(<Skeleton animated={true} />);
		const el = screen.getByRole("status");
		const style = el.getAttribute("style") ?? "";
		expect(style).toContain("shimmer");
	});

	it("has no animation when animated=false", () => {
		render(<Skeleton animated={false} />);
		const el = screen.getByRole("status");
		expect(el).toHaveStyle({ animation: "none" });
	});

	it("applies custom borderRadius", () => {
		render(<Skeleton borderRadius="9999px" />);
		const el = screen.getByRole("status");
		expect(el).toHaveStyle({ borderRadius: "9999px" });
	});

	it("renders with default grey background", () => {
		render(<Skeleton />);
		const el = screen.getByRole("status");
		expect(el).toHaveStyle({ backgroundColor: "#e2e8f0" });
	});
});
