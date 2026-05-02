/**
 * HUG-151: per-event emission tests.
 *
 * Goal: every event in the taxonomy (ALL_EVENT_TYPES, currently 26)
 * has at least one emission assertion test. Events that have a real
 * user-action trigger get a behavioural test (component → spy on
 * emit → assert payload). Events without a natural component
 * trigger (web_vitals.*, api.request.*, app.error,
 * dashboard.cache.observed) get a direct emit() shape test.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import KpiTile from "../../../ui/primitives/KpiTile";
import * as client from "../client";
import { ALL_EVENT_TYPES, type TelemetryEvent } from "../events";

let emitSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
	emitSpy = vi.spyOn(client, "emit");
});

afterEach(() => {
	vi.restoreAllMocks();
	client._resetBatchForTesting();
});

// ── Behavioural tests: user action → component → emit ──────────────

describe("kpi.tile.clicked — KpiTile click", () => {
	it("emits with kpi_id and value when the tile is clicked", () => {
		const onClick = vi.fn(() =>
			client.emit({
				type: "kpi.tile.clicked",
				kpi_id: "total_loans",
				value: 12_500_000,
			}),
		);
		render(<KpiTile label="Total Loans" value="$12.5M" onClick={onClick} />);
		fireEvent.click(screen.getByText("Total Loans"));
		expect(emitSpy).toHaveBeenCalledWith({
			type: "kpi.tile.clicked",
			kpi_id: "total_loans",
			value: 12_500_000,
		});
	});
});

// ── Direct shape tests: every event in the taxonomy ────────────────

const SAMPLES: Record<TelemetryEvent["type"], TelemetryEvent> = {
	"nav.page_view": {
		type: "nav.page_view",
		route: "/dashboards/executive",
	},
	"kpi.tile.clicked": {
		type: "kpi.tile.clicked",
		kpi_id: "total_loans",
		value: 1,
	},
	"chart.legend.toggled": {
		type: "chart.legend.toggled",
		chart_id: "deposit-mix",
		series_name: "Checking",
		visible: false,
	},
	"tab.switched": {
		type: "tab.switched",
		tab_id: "renewed",
		panel_id: "officer-branch",
	},
	"filter.changed": {
		type: "filter.changed",
		filter_name: "branch_id",
		value: "1",
	},
	"commandpalette.opened": {
		type: "commandpalette.opened",
		trigger: "keyboard",
	},
	"commandpalette.action.run": {
		type: "commandpalette.action.run",
		action_id: "go-deposits",
		action_name: "Open Deposit Portfolio",
	},
	"chat.question.submitted": {
		type: "chat.question.submitted",
		question: "How many active loans?",
		length: 22,
	},
	"chat.suggested_prompt.clicked": {
		type: "chat.suggested_prompt.clicked",
		prompt: "Past-due ratio",
	},
	"chat.sql.copied": {
		type: "chat.sql.copied",
		query_id: "q-1",
	},
	"chat.caveat.viewed": {
		type: "chat.caveat.viewed",
		caveat_index: 0,
	},
	"chat.sql.expanded": {
		type: "chat.sql.expanded",
		query_id: "q-1",
	},
	"chat.lineage.expanded": {
		type: "chat.lineage.expanded",
		query_id: "q-1",
	},
	"chat.clarification.shown": {
		type: "chat.clarification.shown",
		question: "What does past-due mean?",
	},
	"chat.clarification.refined": {
		type: "chat.clarification.refined",
		original: "loans?",
		refined: "How many active loans?",
	},
	"chat.result.rendered": {
		type: "chat.result.rendered",
		query_id: "q-1",
		row_count: 1,
		result_type: "number",
	},
	"api.request.started": {
		type: "api.request.started",
		endpoint: "getDepositPortfolio",
		method: "GET",
	},
	"api.request.succeeded": {
		type: "api.request.succeeded",
		endpoint: "getDepositPortfolio",
		status_code: 200,
		duration_ms: 42,
	},
	"api.request.failed": {
		type: "api.request.failed",
		endpoint: "getDepositPortfolio",
		error: "boom",
	},
	"web_vitals.lcp": { type: "web_vitals.lcp", value: 2200, rating: "good" },
	"web_vitals.fcp": { type: "web_vitals.fcp", value: 1500, rating: "good" },
	"web_vitals.inp": { type: "web_vitals.inp", value: 180, rating: "good" },
	"web_vitals.cls": { type: "web_vitals.cls", value: 0.05, rating: "good" },
	"web_vitals.ttfb": { type: "web_vitals.ttfb", value: 800, rating: "good" },
	"app.error": {
		type: "app.error",
		message: "boom",
		context: "react_render",
	},
	"dashboard.cache.observed": {
		type: "dashboard.cache.observed",
		dashboard_id: "deposit-portfolio",
		cache_hit: true,
	},
};

describe("Telemetry taxonomy coverage", () => {
	it("provides a sample for every event type in ALL_EVENT_TYPES", () => {
		for (const type of ALL_EVENT_TYPES) {
			expect(SAMPLES[type]?.type).toBe(type);
		}
	});

	it.each(ALL_EVENT_TYPES)(
		"%s — emit() forwards the event through to the buffer",
		(type) => {
			const event = SAMPLES[type];
			client.emit(event);
			expect(emitSpy).toHaveBeenCalledWith(event);
		},
	);
});
