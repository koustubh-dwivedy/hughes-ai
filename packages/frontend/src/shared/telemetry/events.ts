export interface NavPageView {
	type: "nav.page_view";
	route: string;
	prev_route?: string;
}

export interface KpiTileClicked {
	type: "kpi.tile.clicked";
	kpi_id: string;
	value: number;
	delta?: number;
}

export interface ChartLegendToggled {
	type: "chart.legend.toggled";
	chart_id: string;
	series_name: string;
	visible: boolean;
}

export interface TabSwitched {
	type: "tab.switched";
	tab_id: string;
	panel_id: string;
}

export interface FilterChanged {
	type: "filter.changed";
	filter_name: string;
	value: string;
}

export interface CommandPaletteOpened {
	type: "commandpalette.opened";
	trigger: "keyboard" | "button";
}

export interface CommandPaletteActionRun {
	type: "commandpalette.action.run";
	action_id: string;
	action_name: string;
}

export interface ChatQuestionSubmitted {
	type: "chat.question.submitted";
	question: string;
	length: number;
}

export interface ChatSuggestedPromptClicked {
	type: "chat.suggested_prompt.clicked";
	prompt: string;
}

export interface ChatSqlCopied {
	type: "chat.sql.copied";
	query_id: string;
}

export interface ChatCaveatViewed {
	type: "chat.caveat.viewed";
	caveat_index: number;
}

export interface ChatSqlExpanded {
	type: "chat.sql.expanded";
	query_id: string;
}

export interface ChatLineageExpanded {
	type: "chat.lineage.expanded";
	query_id: string;
}

export interface ChatClarificationShown {
	type: "chat.clarification.shown";
	question: string;
}

export interface ChatClarificationRefined {
	type: "chat.clarification.refined";
	original: string;
	refined: string;
}

export type ChatResultType = "number" | "table" | "chart" | "clarification";

export interface ChatResultRendered {
	type: "chat.result.rendered";
	query_id: string;
	row_count: number;
	result_type: ChatResultType;
}

export interface ApiRequestStarted {
	type: "api.request.started";
	endpoint: string;
	method: string;
}

export interface ApiRequestSucceeded {
	type: "api.request.succeeded";
	endpoint: string;
	status_code: number;
	duration_ms: number;
	cache?: "hit" | "miss";
	retry_count?: number;
}

export interface ApiRequestFailed {
	type: "api.request.failed";
	endpoint: string;
	status_code?: number;
	error: string;
	duration_ms?: number;
	retry_count?: number;
}

type VitalsRating = "good" | "needs-improvement" | "poor";

export interface WebVitalsLcp {
	type: "web_vitals.lcp";
	value: number;
	rating: VitalsRating;
}

export interface WebVitalsFcp {
	type: "web_vitals.fcp";
	value: number;
	rating: VitalsRating;
}

export interface WebVitalsInp {
	type: "web_vitals.inp";
	value: number;
	rating: VitalsRating;
}

export interface WebVitalsCls {
	type: "web_vitals.cls";
	value: number;
	rating: VitalsRating;
}

export interface WebVitalsTtfb {
	type: "web_vitals.ttfb";
	value: number;
	rating: VitalsRating;
}

export interface AppError {
	type: "app.error";
	message: string;
	stack?: string;
	context?: string;
}

export interface DashboardCacheObserved {
	type: "dashboard.cache.observed";
	dashboard_id: string;
	cache_hit: boolean;
}

export type TelemetryEvent =
	| NavPageView
	| KpiTileClicked
	| ChartLegendToggled
	| TabSwitched
	| FilterChanged
	| CommandPaletteOpened
	| CommandPaletteActionRun
	| ChatQuestionSubmitted
	| ChatSuggestedPromptClicked
	| ChatSqlCopied
	| ChatCaveatViewed
	| ChatSqlExpanded
	| ChatLineageExpanded
	| ChatClarificationShown
	| ChatClarificationRefined
	| ChatResultRendered
	| ApiRequestStarted
	| ApiRequestSucceeded
	| ApiRequestFailed
	| WebVitalsLcp
	| WebVitalsFcp
	| WebVitalsInp
	| WebVitalsCls
	| WebVitalsTtfb
	| AppError
	| DashboardCacheObserved;

export const ALL_EVENT_TYPES: Array<TelemetryEvent["type"]> = [
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
];
