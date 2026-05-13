/**
 * Regression tests for the shared categorical XAxis + the
 * `truncateLabel` formatter that backs it. These pin the configured
 * angle, height, interval, and truncation behavior so future chart
 * additions automatically inherit non-colliding axis defaults.
 */

import { render } from "@testing-library/react";
import { Bar, BarChart, XAxis } from "recharts";
import { describe, expect, it } from "vitest";
import { CHART_MARGIN, categoricalXAxisProps } from "./CategoricalXAxis";
import { truncateLabel } from "./formatters";

describe("truncateLabel", () => {
	it("returns the input unchanged when within the cap", () => {
		expect(truncateLabel(16)("Auto Loans")).toBe("Auto Loans");
	});

	it("truncates and appends an ellipsis when over the cap", () => {
		expect(truncateLabel(16)("Commercial Real Estate Mortgage")).toBe(
			"Commercial Real…",
		);
	});

	it("handles null / undefined as empty string", () => {
		expect(truncateLabel(8)(null)).toBe("");
		expect(truncateLabel(8)(undefined)).toBe("");
	});

	it("supports edge case where cap < 1", () => {
		// Caller passed a nonsense cap; degrade to a lone ellipsis
		// rather than throwing.
		expect(truncateLabel(0)("anything")).toBe("…");
	});
});

describe("categoricalXAxisProps", () => {
	it("returns the angle, interval, height, and anchor recharts needs", () => {
		const props = categoricalXAxisProps({ dataKey: "label" });
		expect(props.dataKey).toBe("label");
		expect(props.interval).toBe(0);
		expect(props.angle).toBe(-30);
		expect(props.textAnchor).toBe("end");
		expect(props.height).toBe(64);
		expect(typeof props.tickFormatter).toBe("function");
	});

	it("truncates labels via the bundled tickFormatter", () => {
		const { tickFormatter } = categoricalXAxisProps({ dataKey: "label" });
		expect(tickFormatter("Auto Loans")).toBe("Auto Loans");
		expect(tickFormatter("Commercial Real Estate Mortgage")).toBe(
			"Commercial Real…",
		);
	});

	it("respects a custom truncate cap", () => {
		const { tickFormatter } = categoricalXAxisProps({
			dataKey: "label",
			truncate: 6,
		});
		expect(tickFormatter("Mortgage")).toBe("Mortg…");
	});

	it("respects a custom height (e.g. tighter row for short labels)", () => {
		const props = categoricalXAxisProps({ dataKey: "label", height: 32 });
		expect(props.height).toBe(32);
	});

	it("renders correctly when spread onto a real recharts <XAxis>", () => {
		// Smoke test: feeding the props into a BarChart with an
		// explicit width/height should produce SVG <text> children,
		// proving recharts recognizes the axis (which it WOULD NOT if
		// we'd wrapped it inside a custom component).
		const { container } = render(
			<BarChart
				width={800}
				height={300}
				data={[
					{ label: "Auto Loans", v: 1 },
					{ label: "Home Equity", v: 2 },
				]}
				margin={CHART_MARGIN}
			>
				<XAxis {...categoricalXAxisProps({ dataKey: "label" })} />
				<Bar dataKey="v" />
			</BarChart>,
		);
		const textEls = container.querySelectorAll("text");
		expect(textEls.length).toBeGreaterThan(0);
	});

	it("exports CHART_MARGIN with bottom padding for the angled labels", () => {
		expect(CHART_MARGIN.bottom).toBeGreaterThan(0);
	});
});
