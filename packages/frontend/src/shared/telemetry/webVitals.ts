import { type Metric, onCLS, onFCP, onINP, onLCP, onTTFB } from "web-vitals";
import { emit } from "./client";
import type { TelemetryEvent } from "./events";

/**
 * Map a web-vitals callback to its telemetry event type. Returning the
 * mapping (rather than the literal string keys spread across helpers)
 * keeps the call sites uniform and lets us iterate the registrations.
 */
const SUBSCRIBERS: Array<
	[(cb: (m: Metric) => void) => void, TelemetryEvent["type"]]
> = [
	[onLCP, "web_vitals.lcp"],
	[onFCP, "web_vitals.fcp"],
	[onINP, "web_vitals.inp"],
	[onCLS, "web_vitals.cls"],
	[onTTFB, "web_vitals.ttfb"],
];

function metricToEvent(
	type: TelemetryEvent["type"],
	metric: Metric,
): TelemetryEvent {
	return {
		type,
		value: metric.value,
		rating: metric.rating,
		// biome-ignore lint/suspicious/noExplicitAny: discriminated union — type drives the runtime shape
	} as any;
}

/**
 * Subscribe to all 5 Core Web Vitals (LCP, FCP, INP, CLS, TTFB) and
 * emit one telemetry event per metric per page-view. web-vitals fires
 * each callback at most once per page so de-duplication is implicit.
 */
export function initWebVitals(): void {
	for (const [register, type] of SUBSCRIBERS) {
		register((metric) => emit(metricToEvent(type, metric)));
	}
}
