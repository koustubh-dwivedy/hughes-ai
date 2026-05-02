import { afterEach, describe, expect, it, vi } from "vitest";
import type { Metric } from "web-vitals";

const onLCP = vi.fn();
const onFCP = vi.fn();
const onINP = vi.fn();
const onCLS = vi.fn();
const onTTFB = vi.fn();

vi.mock("web-vitals", () => ({
	onLCP: (cb: (m: Metric) => void) => onLCP(cb),
	onFCP: (cb: (m: Metric) => void) => onFCP(cb),
	onINP: (cb: (m: Metric) => void) => onINP(cb),
	onCLS: (cb: (m: Metric) => void) => onCLS(cb),
	onTTFB: (cb: (m: Metric) => void) => onTTFB(cb),
}));

import * as telemetry from "./client";
import { initWebVitals } from "./webVitals";

afterEach(() => {
	vi.clearAllMocks();
	vi.restoreAllMocks();
});

function fakeMetric(value: number, rating: Metric["rating"]): Metric {
	return {
		name: "LCP",
		value,
		rating,
		delta: 0,
		entries: [],
		id: "fake",
		navigationType: "navigate",
	};
}

describe("initWebVitals — registers a callback for every Core Web Vital", () => {
	it("subscribes to LCP, FCP, INP, CLS, TTFB exactly once each", () => {
		initWebVitals();
		expect(onLCP).toHaveBeenCalledTimes(1);
		expect(onFCP).toHaveBeenCalledTimes(1);
		expect(onINP).toHaveBeenCalledTimes(1);
		expect(onCLS).toHaveBeenCalledTimes(1);
		expect(onTTFB).toHaveBeenCalledTimes(1);
	});
});

describe("initWebVitals — emits telemetry when a metric resolves", () => {
	it("emits web_vitals.lcp with the metric value + rating", () => {
		const spy = vi.spyOn(telemetry, "emit");
		initWebVitals();
		const cb = onLCP.mock.calls[0]?.[0] as (m: Metric) => void;
		cb(fakeMetric(2200, "good"));
		expect(spy).toHaveBeenCalledWith({
			type: "web_vitals.lcp",
			value: 2200,
			rating: "good",
		});
	});

	it("emits web_vitals.fcp with rating needs-improvement", () => {
		const spy = vi.spyOn(telemetry, "emit");
		initWebVitals();
		const cb = onFCP.mock.calls[0]?.[0] as (m: Metric) => void;
		cb(fakeMetric(2500, "needs-improvement"));
		expect(spy).toHaveBeenCalledWith({
			type: "web_vitals.fcp",
			value: 2500,
			rating: "needs-improvement",
		});
	});

	it("emits web_vitals.inp", () => {
		const spy = vi.spyOn(telemetry, "emit");
		initWebVitals();
		const cb = onINP.mock.calls[0]?.[0] as (m: Metric) => void;
		cb(fakeMetric(180, "good"));
		expect(spy).toHaveBeenCalledWith({
			type: "web_vitals.inp",
			value: 180,
			rating: "good",
		});
	});

	it("emits web_vitals.cls", () => {
		const spy = vi.spyOn(telemetry, "emit");
		initWebVitals();
		const cb = onCLS.mock.calls[0]?.[0] as (m: Metric) => void;
		cb(fakeMetric(0.05, "good"));
		expect(spy).toHaveBeenCalledWith({
			type: "web_vitals.cls",
			value: 0.05,
			rating: "good",
		});
	});

	it("emits web_vitals.ttfb with rating poor", () => {
		const spy = vi.spyOn(telemetry, "emit");
		initWebVitals();
		const cb = onTTFB.mock.calls[0]?.[0] as (m: Metric) => void;
		cb(fakeMetric(2800, "poor"));
		expect(spy).toHaveBeenCalledWith({
			type: "web_vitals.ttfb",
			value: 2800,
			rating: "poor",
		});
	});
});
