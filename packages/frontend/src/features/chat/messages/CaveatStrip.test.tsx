import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as telemetry from "../../../shared/telemetry/client";
import CaveatStrip from "./CaveatStrip";

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CaveatStrip", () => {
	it("renders nothing when caveats list is empty", () => {
		const { container } = render(<CaveatStrip caveats={[]} />);
		expect(container.firstChild).toBeNull();
	});

	it("renders each caveat as a visible Tag", () => {
		render(
			<CaveatStrip caveats={["Excludes test loans", "Synthetic data only"]} />,
		);
		expect(screen.getByText("Excludes test loans")).toBeInTheDocument();
		expect(screen.getByText("Synthetic data only")).toBeInTheDocument();
	});

	it("emits chat.caveat.viewed once per caveat on mount", () => {
		const spy = vi.spyOn(telemetry, "emit");
		render(<CaveatStrip caveats={["A", "B", "C"]} />);
		expect(spy).toHaveBeenCalledTimes(3);
		expect(spy).toHaveBeenNthCalledWith(1, {
			type: "chat.caveat.viewed",
			caveat_index: 0,
		});
		expect(spy).toHaveBeenNthCalledWith(2, {
			type: "chat.caveat.viewed",
			caveat_index: 1,
		});
		expect(spy).toHaveBeenNthCalledWith(3, {
			type: "chat.caveat.viewed",
			caveat_index: 2,
		});
	});

	it("uses warning variant tags (visual + a11y region)", () => {
		render(<CaveatStrip caveats={["Heads up"]} />);
		expect(
			screen.getByRole("region", { name: "Result caveats" }),
		).toBeInTheDocument();
	});
});
