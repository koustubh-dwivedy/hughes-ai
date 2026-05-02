import { describe, expect, it } from "vitest";
import { ALL_EVENT_TYPES, type TelemetryEvent } from "../events";

describe("ALL_EVENT_TYPES", () => {
	it("contains exactly 26 event names", () => {
		expect(ALL_EVENT_TYPES).toHaveLength(26);
	});

	it("matches expected event taxonomy", () => {
		expect(ALL_EVENT_TYPES).toEqual([
			"nav.page_view",
			"kpi.tile.clicked",
			"chart.legend.toggled",
			"tab.switched",
			"filter.changed",
			"commandpalette.opened",
			"commandpalette.action.run",
			"chat.question.submitted",
			"chat.suggested_prompt.clicked",
			"chat.sql.copied",
			"chat.caveat.viewed",
			"chat.sql.expanded",
			"chat.lineage.expanded",
			"chat.clarification.shown",
			"chat.clarification.refined",
			"chat.result.rendered",
			"api.request.started",
			"api.request.succeeded",
			"api.request.failed",
			"web_vitals.lcp",
			"web_vitals.fcp",
			"web_vitals.inp",
			"web_vitals.cls",
			"web_vitals.ttfb",
			"app.error",
			"dashboard.cache.observed",
		]);
	});

	it("contains no duplicate event types", () => {
		const unique = new Set(ALL_EVENT_TYPES);
		expect(unique.size).toBe(ALL_EVENT_TYPES.length);
	});
});

// Type-level test: a valid event compiles
const _validEvent: TelemetryEvent = {
	type: "kpi.tile.clicked",
	kpi_id: "total_loans",
	value: 12_500_000,
};
void _validEvent;

// Type-level test: a valid web-vitals event compiles
const _vitalsEvent: TelemetryEvent = {
	type: "web_vitals.lcp",
	value: 2500,
	rating: "good",
};
void _vitalsEvent;
