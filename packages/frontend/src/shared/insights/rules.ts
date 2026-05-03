// Deterministic, rule-based insight generators. One function per chart type.
// Each takes the raw chart data and returns 1–3 plain-English bullets plus a
// tone (info / warn / success / neutral). No LLM calls — keeps the demo fast,
// predictable, and free of API spend, and the math is unit-testable.

import type { InsightTone } from "../components/InsightCard";

export interface Insight {
	bullets: string[];
	tone: InsightTone;
}

const NEUTRAL: Insight = { bullets: [], tone: "neutral" };

function fmtPct(n: number, digits = 1): string {
	return `${n.toFixed(digits)}%`;
}

function fmtMillions(n: number): string {
	if (Math.abs(n) >= 1_000_000) {
		return `$${(n / 1_000_000).toFixed(1)}M`;
	}
	if (Math.abs(n) >= 1_000) {
		return `$${(n / 1_000).toFixed(0)}K`;
	}
	return `$${Math.round(n)}`;
}

// ── Past Due trend (3 buckets, 13mo) ─────────────────────────────────────────

export interface DelinquencyTrendPoint {
	period: string;
	"30-59": number;
	"60-89": number;
	"90+": number;
}

export function pastDueTrendInsight(
	series: DelinquencyTrendPoint[],
): Insight {
	if (series.length < 2) return NEUTRAL;
	const last = series[series.length - 1];
	const prev = series[series.length - 2];
	const lastTotal = last["30-59"] + last["60-89"] + last["90+"];
	const prevTotal = prev["30-59"] + prev["60-89"] + prev["90+"];
	if (prevTotal === 0) return NEUTRAL;
	const change = (lastTotal - prevTotal) / prevTotal;

	const ninetyShare =
		lastTotal === 0 ? 0 : (last["90+"] / lastTotal) * 100;
	const bullets: string[] = [];
	let tone: InsightTone = "info";

	if (change > 0.05) {
		bullets.push(
			`Past due balances rose ${fmtPct(change * 100)} month-over-month — worth reviewing officer pipelines.`,
		);
		tone = "warn";
	} else if (change < -0.05) {
		bullets.push(
			`Past due balances fell ${fmtPct(Math.abs(change) * 100)} month-over-month — collections is gaining ground.`,
		);
		tone = "success";
	} else {
		bullets.push(
			`Past due roughly flat (${fmtPct(change * 100)} MoM). No regime change.`,
		);
	}

	if (ninetyShare > 35) {
		bullets.push(
			`90+ days late is ${fmtPct(ninetyShare)} of total past due — late-stage delinquency is the dominant slice.`,
		);
		if (tone !== "warn") tone = "warn";
	}

	return { bullets, tone };
}

// ── Past Due ratio trend ─────────────────────────────────────────────────────

export interface RatioTrendPoint {
	period: string;
	value: number; // already in percent
}

export function ratioTrendInsight(series: RatioTrendPoint[]): Insight {
	if (series.length < 2) return NEUTRAL;
	const last = series[series.length - 1].value;
	const first = series[0].value;
	const change = last - first;
	const tone: InsightTone =
		last < 1.5 ? "success" : last < 2.5 ? "info" : "warn";
	const bullets = [
		`Latest past-due ratio: ${fmtPct(last)} (industry healthy band: under 1.5%).`,
	];
	if (Math.abs(change) >= 0.1) {
		const dir = change > 0 ? "up" : "down";
		bullets.push(
			`Trending ${dir} ${fmtPct(Math.abs(change))} over the last ${series.length - 1} months.`,
		);
	}
	return { bullets, tone };
}

// ── Deposit mix concentration ────────────────────────────────────────────────

export interface MixSlice {
	label: string;
	value: number;
}

export function depositMixInsight(slices: MixSlice[]): Insight {
	if (slices.length === 0) return NEUTRAL;
	const total = slices.reduce((s, x) => s + x.value, 0);
	if (total === 0) return NEUTRAL;
	const sorted = [...slices].sort((a, b) => b.value - a.value);
	const top = sorted[0];
	const topShare = (top.value / total) * 100;
	const bullets: string[] = [];
	let tone: InsightTone = "info";

	bullets.push(
		`Largest product is ${top.label} at ${fmtPct(topShare)} of the deposit book (${fmtMillions(top.value)}).`,
	);

	if (topShare > 50) {
		bullets.push(
			`Concentration risk: more than half of deposits sit in one product.`,
		);
		tone = "warn";
	} else if (sorted.length >= 3) {
		const top3 = sorted.slice(0, 3).reduce((s, x) => s + x.value, 0);
		bullets.push(
			`Top 3 products carry ${fmtPct((top3 / total) * 100)} of total deposits.`,
		);
	}

	return { bullets, tone };
}

// ── Officer load: who carries the past-due balance ───────────────────────────

export interface OfficerRow {
	period: string;
	balance: number;
}

export function officerLoadInsight(officers: OfficerRow[]): Insight {
	if (officers.length === 0) return NEUTRAL;
	const total = officers.reduce((s, o) => s + o.balance, 0);
	if (total === 0) return NEUTRAL;
	const sorted = [...officers].sort((a, b) => b.balance - a.balance);
	const top = sorted[0];
	const share = (top.balance / total) * 100;
	const bullets = [
		`${top.period} carries ${fmtPct(share)} of past-due balance (${fmtMillions(top.balance)}).`,
	];
	const tone: InsightTone =
		share > 40 ? "warn" : share > 25 ? "info" : "neutral";
	if (share > 40) {
		bullets.push(
			`Single-officer concentration above 40% — consider load-balancing or coaching.`,
		);
	}
	return { bullets, tone };
}

// ── Loans & rate spread combo ────────────────────────────────────────────────

export interface ComboPoint {
	period: string;
	bar: number; // loans $M
	line: number; // spread %
}

export function loanRateSpreadInsight(series: ComboPoint[]): Insight {
	if (series.length < 3) return NEUTRAL;
	const last = series[series.length - 1];
	const prev3 = series.slice(-4, -1);
	const avg3 = prev3.reduce((s, p) => s + p.line, 0) / prev3.length;
	const direction =
		last.line > avg3 + 0.05
			? "expanding"
			: last.line < avg3 - 0.05
				? "compressing"
				: "stable";
	const bullets = [
		`Margin currently ${fmtPct(last.line)} (3-mo avg ${fmtPct(avg3)}) — ${direction}.`,
	];
	let tone: InsightTone = "info";
	if (last.line < 2) {
		bullets.push(
			`Spread under 200 bps — net interest margin is thin, watch funding costs.`,
		);
		tone = "warn";
	} else if (direction === "expanding") {
		tone = "success";
	}
	return { bullets, tone };
}

// ── Watchlist trend ──────────────────────────────────────────────────────────

export interface WatchlistPoint {
	month: string;
	count: number;
}

export function watchlistTrendInsight(points: WatchlistPoint[]): Insight {
	if (points.length < 2) return NEUTRAL;
	const last = points[points.length - 1].count;
	const first = points[0].count;
	const delta = last - first;
	const bullets = [
		`Loans under watch: ${last} (was ${first} ${points.length - 1} months ago).`,
	];
	let tone: InsightTone = "info";
	if (delta > 0) {
		bullets.push(`Up ${delta} over the period — earlier-stage risk is rising.`);
		tone = "warn";
	} else if (delta < 0) {
		bullets.push(`Down ${Math.abs(delta)} — fewer loans need close monitoring.`);
		tone = "success";
	}
	return { bullets, tone };
}

// ── Change-by-product waterfall ──────────────────────────────────────────────

export interface WaterfallBar {
	label: string;
	value: number; // already in $M (from caller)
}

export function changeByProductInsight(bars: WaterfallBar[]): Insight {
	if (bars.length === 0) return NEUTRAL;
	const sorted = [...bars].sort((a, b) => b.value - a.value);
	const top = sorted[0];
	const bottom = sorted[sorted.length - 1];
	const bullets: string[] = [];
	if (top.value > 0) {
		bullets.push(
			`${top.label} contributed +$${top.value.toFixed(1)}M — biggest gainer this period.`,
		);
	}
	if (bottom.value < 0 && bottom !== top) {
		bullets.push(
			`${bottom.label} pulled back ${bottom.value.toFixed(1)}M — biggest drag.`,
		);
	}
	if (bullets.length === 0) {
		bullets.push("No standout movers — book changes were balanced across products.");
	}
	const tone: InsightTone =
		bottom.value < -1 ? "warn" : top.value > 1 ? "success" : "info";
	return { bullets, tone };
}
